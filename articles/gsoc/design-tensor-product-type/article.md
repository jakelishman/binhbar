`Qobj` instantiation and mathematical operations have a large overhead, mostly
because of handling the `dims` parameter in tensor-product spaces.  I'm
proposing one possible way to speed this up, while also gaining some additional
safety and knowledge about mathematical operations on tensor-product spaces.

The steps:

1. rigourously define the "grammar" of `dims`, and allow all of `dimensions.py`
   to assume that this grammar is followed to speed up parsing
2. maintain a private data structure type `dimensions._Parsed` inside `Qobj`
   which is constructed once, and keeps all details of the parsing so they need
   not be repeated.  Determine `Qobj.type` from this data structure
3. maintain knowledge of the individual `type` of every subspace in the full
   Hilbert space (e.g. with a list).  There is still a "global" `Qobj.type`, but
   this can now be one in the set `{'bra', 'ket', 'oper', 'scalar', 'super',
   'other'}`.  `'other'` is for when the individual elements do not all match
   each other.  Individual elements cannot be `'other'`.  `'scalar'` is added to
   operations can keep track of tensor elements which have been contracted, say
   by a `bra-ket` product---operations will then broadcast scalar up to the
   correct dimensions on certain operations.
4. dimension parsing is now sped up by using the operation-specific type
   knowledge.  For example, `bra + bra -> bra`, and `ket.dag() -> bra`.  Step 3
   is necessary to allow matrix multiplication to work.  These lookups could be
   done with enum values instead of string hashing.

_Note:_ this is part of a design discussion for the next major release of QuTiP.
I originally wrote this on 2020-07-13, and any further discussion may be found
at [the corresponding GitHub issue](https://github.com/qutip/qutip/issues/1320).

---

As of QuTiP 4.5 (and all previous versions), `Qobj` instantiation is slow and
this permeates through to all operations on `Qobj`.  Matrix multiplication,
scalar multiplication, addition and so forth all need to instantiate new `Qobj`
instances, and the time penalty for this is on the order of ~50µs per object.
This results in more and more code than needs to bypass `Qobj` for speed, and in
some cases (e.g. `qutip.control`) makes the use of `Qobj` prohibitively
expensive.  This obviously is not ideal, since `Qobj` is our primary data type.

The majority of this time loss is due to inferring the type of an object from
its dimensions, and on unnecessary copying of data at initialisation.  This is
exacerbated by operations often instantiating an `out` parameter as `out =
Qobj()`, and then doing things like `out.dims = ...`, `out.data = ...`.  This
causes runtime checks to be done at every stage, so the penalty of
initialisation can sometimes be paid several times over in simple operations (a
particularly notable example is in the implicit promotion of scalars to
operators in addition, taking over 500µs to execute `1 + qutip.qeye(2)`).  A lot
of this can be completely avoided, however, simply by instantiating the objects
using _all_ known information, not relying on inference.

In particular, various operations _know_ what the type of their outcome is by a
simple lookup table: addition is only defined between operations of the same
type and maintains that type, whereas the adjoint has the mapping

```python
_ADJOINT_TYPE_LOOKUP = {
    'ket': 'bra',
    'bra': 'ket',
    'oper': 'oper',
    'super': 'super',
}
```

If this information is supplied to `Qobj.__init__` (and the fact that it need
not copy data we've created specially for it...), we can hugely slash the
overhead of mathematical operations while maintaining their safety.

The issues start to come once we look at matrix multiplication and
tensor-product spaces.  The tensor allows us to construct objects which are a
mixture of several different types, and matrix multiplication wants to be able
to contract scalar product spaces so that `bra * ket` gives a scalar.

## Problems with dimension handling

The current dimension handling in QuTiP is simple and intuitive until
tensor-product structures are considered.  At this point, it starts to become
more complicated.  In particular, the `type` of a `Qobj` is tied to its
dimensions, but it becomes difficult to define this once there is tensor product
structure.  Some of this is because QuTiP allows us to construct objects which
do not have a really rigourous mathematical backing to them, such as `I . |g>` -
the tensor product of an operator and a ket.  QuTiP assigns this a type
`'oper'`, though the way it reaches this decision is more like:

1. is it a ket? [no]
2. is it a bra? [no]
3. is it a super-operator? [no]
4. if here, it must be an operator

Such objects do have a use.  Let's say we have a system with two computational
qubits and one ancillary qubit, we've performed a calculation on it and ended up
in some state `|x> = |a>.|b>.|c>`, and we want to extract the computational
subspace when the ancilla bit is projected onto `|0>`.  We can do this in a
mathematically rigourous way with

```python
>>> projector = qutip.tensor(qutip.qeye([2, 2]), qutip.basis(2, 0).proj())
>>> (projector * x).ptrace([0, 1])
Quantum object: dims = [[2, 2], [2, 2]], shape = (4, 4), type = oper, isherm = True
...
```

which will always return a density matrix.  Alternatively, we can instead define
the operator (note `proj()` to create `|g><g|` has become `dag()` to simply make
`<g|`) as

```python
>>> projector = qutip.tensor(qutip.qeye([2, 2]), qutip.basis(2, 0).dag())
>>> projector * x
Quantum object: dims = [[2, 2], [1, 1]], shape = (4, 1), type = ket
...
```

which gets us what we wanted.

This is not necessarily _common_, but it is useful in some circumstances.

## Other problem discussions

There have been some cases of complaint about the handling of tensor-product
spaces in QuTiP in the past (see [this discussion in the Google
group](https://groups.google.com/forum/#!msg/qutip/NAGU4iKZNBY/NjqiFEkyDlkJ)),
but these largely revolve around people not liking the idea that we enforce the
tensor structure to be maintained at all.  My reading of these issues is that
some people would like to see `dims` removed, or make mathematical operations
effectively ignore it.

## Solutions

### Rejections

Personally, I think enforcing the tensor product structure catches a whole lot
of potential issues in code when working with objects in different Hilbert
spaces, and so far I've not actually seen any examples where I think frequent
overriding of the `dims` is necessary.  I'd argue that the `Qobj` constructor
taking a `dims` parameter is sufficient for any use-case which needs to manually
set the dimensions because they're passing in an object constructed outside of
QuTiP functions.

Removing `dims` also makes a lot of operations harder to do.  Various places in
the code permute the order of the tensored spaces, and dropping `dims` means
that the user has to "remember" the tensor product structure themselves so that
they can pass it in, and we can then know what to reorder.  Clearly this is
undesirable---the `dims` are a non-computable property of the object, and
therefore should be carried around as a data attribute on the class.

The alternative in the Google group that's sometimes suggested is to keep `dims`
for these use-cases, but make it more of a suggestion, so that any two objects
which satisfy `left.shape == right.shape` should be compatible for addition-like
operations, and ones which satisfy `left.shape[1] == right.shape[0]` should be
compatible for matrix-multiplication-like operations.  Again, I personally would
tend to reject this on the grounds that enforcing the tensor-product structure
is respected is a core part of what `Qobj` does; it ensures that the operations
are mathematically possible, and that operations between different Hilbert
spaces are not mixed.

### Proposal

First off, we can sidestep some of these issues by improving library code which
creates `Qobj` instances.  Operations like `Qobj.__add__` already know exactly
what the output dimensions are, what the the type must be, and other things like
if Hermiticity has been preserved.  We move away from the outdated style of

```python
out = Qobj()
out.data = left.data + right.data
out.dims = left.dims
...
```

to one which passes _all_ the information in one go:

```python
out = Qobj(left.data + right.data,
           copy=False,
           dims=left.dims,
           type=left.type,
           isherm=left._isherm and right._isherm)
```

This is more verbose, but significantly faster.  With no other changes to the
code, doing this can save around one-quarter of the overhead on several `Qobj`
operations.  Moving to the new data-layer types also gets large improvements in
instantiation time.

This is fine, except for matrix multiplication of tensor structures.  In these,
like in the example above, the matrix multiplication can cause tensor structures
to contract, and so they then become incompatible with their previous Hilbert
spaces.  If we instead maintain a _list_ of `'type'` and introduce a `'scalar'`
type, such objects can sensibly be broadcast back up to the correct size when
needed, treating the spaces containing as identities of the correct dimension.
I envisage that this may have some nice use-cases within `qip`, for example a
gate on a single qubit could be represented by a two-by-two matrix with all
other dimensions scalars, rather than requiring the whole Hilbert space to be
represented all the time.  Optimisations can be done using only the required
elements of the subspace, and only broadcast up to the full representation once
at the end.

Further, we can ease the burden of parsing the dimensions in the first place.  I
haven't fully attempted this yet so I don't have full details on this, but I
imagine there is some internal information we can keep after a single parsing
pass that will make other operations simpler.  This is particularly true of
super-operators, which often care about the input and output shapes of the
spaces, necessitating several more calls to `np.prod`.  Since this information
_has_ to be computed at type-inference time, it's easy to save it and remove the
overhead.  I'd propose having this type be internal, something like
`dimensions.Parsed` and storing it as a protected attribute on `Qobj` instances.
