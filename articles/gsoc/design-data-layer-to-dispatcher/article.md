This post is partial documentation for the implementation of the data-layer that
I wrote in the last week or so as part of [Google Summer of Code][gsoc] with
[QuTiP](http://qutip.org/).  I may return to talk a bit more about how various
algorithms are achieved internally, but for now, this is some indication of what
I've been working on.

[gsoc]: https://summerofcode.withgoogle.com/

I had previously replaced the old `fast_csr_matrix` type with the new, custom
`CSR` type as the data backing for `Qobj`, and all internal QuTiP data
representations.  This produced some speed-ups in some places due to improved
algorithms and better cache usage in places, but its principle advantage was the
massive reduction in overhead for function calls between Python and C space,
which largely affected small objects.

The full aim, however, is to have QuTiP 5 support many different data
representations as the backing of `Qobj`, and use the most suitable
representation for the given data. This will not require every single QuTiP
function to have an exponential number of versions for every possible
combination of inputs, but only to have specialisations for the most common data
combinations.  This concept is the "data layer".

All code examples in this post are prefixed with

```python
>>> from qutip.core import data
```

## Specification

The core to achieving this is fast, fully specified inter-conversion between all
known data types, and efficient multiple-dispatch for mathematical operations.
There are then four principle components of the data-layer:

1. a creation routine which returns an appropriate data-layer type given some
   arbitrary Python object (`data.create`)
2. a routine which can perform the conversion from any data-layer type to any
   other data-layer type (`data.to`)
3. completely specialised mathematical operations (e.g.
   `data.add_csr_dense_dense(CSR, Dense) -> Dense`)
4. an object which provides multiple dispatch operations on its input arguments
   to use an exact specialisation (defined in item 3) if known, or uses the
   conversion routine (item 2) to convert the inputs into ones matching a
   specialisation if not: `data.Dispatcher`.  The exported mathematical
   functions will all be instances of this type.

The minimum work needed to define a new data-layer type is to provide `data.to`
with two conversion functions; one into the new type from a current data-layer
type, and one which converts the new type _into_ a current data-layer type.
Once this is done, every single QuTiP component will be able to use the new
data-layer type, although until specialisations are given which use it, it will
always be achieved by conversion to another type, and conversion back.  In this
way, a new type can be added incrementally, with only the most common operations
needing to be defined to get good efficiency.

**Important caveat:** the data layer operates only on _exact_ types; subclasses
of defined types will be treated as completely different types.  This is to do
with keeping the computational complexity of multiple-dispatch operations as
O(1) (i.e. I don't know how to do multiple dispatch in constant time allowing
inheritance).

### `data.to`: conversion between types

```python
>>> matrix = data.dense.identity(5)
>>> matrix
Dense(shape=(5, 5), fortran=True)
>>> data.to(data.CSR, matrix)
CSR(shape=(5, 5), nnz=5)
```

```python
>>> data.to[data.CSR, data.Dense]
<converter to CSR from Dense>
```

```python
>>> data.to[data.Dense]
<converter to Dense>
```

```python
>>> class NewDataType:
...     # [...]
>>> def new_from_dense(matrix: data.Dense) -> NewDataType:
...     # [...]
>>> def dense_from_new(matrix: NewDataType) -> data.Dense:
...     # [...]
>>> data.to.add_conversions([
...     (NewDataType, data.Dense, new_from_dense),
...     (data.Dense, NewDataType, dense_from_new),
... ])
>>> data.to[data.CSR, NewDataType]
<converter to CSR from NewDataType>
```

#### Basic usage

Convert data into a different type.  This object is the knowledge source for
every allowable data-layer type in QuTiP, and provides the conversions between
all of them.

The base use is to call this object as a function with signature

```text
    (type, data) -> converted_data
```

where `type` is a type object (such as `data.CSR`, or that obtained by calling
`type(matrix)`) and `data` is data in a data-layer type.  If you want to create
a data-layer type from non-data-layer data, use `create` instead.


You can get individual converters by using the key-lookup syntax.  For example,
the item

```python
    to[CSR, Dense]
```

is a callable which accepts arguments of type `Dense` and returns the equivalent
item of type `CSR`.  You can also get a generic converter to a particular data
type if only one type is specified, so

```python
    to[Dense]
```

is a callable which accepts all known (at the time of the lookup) data-layer
types, and converts them to `Dense`.  See the "Efficiency notes" section below
for more detail.


Internally, the conversion process may go through several steps if new
data-layer types have been defined with few conversions specified between them
and the pre-existing converters.  The first-class QuTiP data types `Dense` and
`CSR` will typically have the fastest connectivity.


#### Adding new types

You can add new data-layer types by calling the `add_conversions` method of this
object, and then rebuilding all of the mathematical dispatchers.  See the
docstring of that method for more information.


#### Implementation details

Not all conversions have to be specified for a new type; it is enough to have
just one to and from a known type to a new type.  The rest of the conversion
graph is built up by graph traversal over known types (the graph is
reconstructed whenever `add_conversions` is called), where the approximate cost
of each function is used as the weight of an "edge" joining two data-layer type
"vertices".  The shortest path conversion function is constructed and stored (as
the interal type `data.convert._converter`) for each pair of types.  We
willingly sacrifice memory efficiency for speed-efficiency here, since we expect
there to be few data-layer types, but for the calls to happen millions of times.

The converters returned by single-key access (e.g. `data.to[data.Dense]`) are
constructed individually on a call to `__getitem__`, and are instances of the
private type `data.convert._partial_converter`, which internally stores a
reference to every "full" converter, and dispatches to the correct one when
called.

The entire `data.to` object and all subsidiary `_converter` and
`_partial_converter` objects are `pickle`-able. 


#### Efficiency notes

From an efficiency perspective, there is very little benefit to using the
key-lookup syntax.  Internally, `to(to_type, data)` effectively calls
`to[to_type, type(data)]`, so storing the object elides the creation of a single
tuple and a dict lookup, but the cost of this is generally less than 500ns.
Using the one-argument lookup (e.g. `to[Dense]`) is no more efficient than the
general call at all, but can be used in cases where a single callable is
required and is more efficient, concise and descriptive than
`functools.partial`.



### `data.Dispatcher`: arbitrary multiple-dispatch operations

```python
>>> import scipy.sparse
>>> import numpy as np
>>> a = data.CSR(scipy.sparse.csr_matrix(np.random.rand(5, 5)))
>>> b = data.Dense(np.random.rand(5, 5))
>>> data.add(a, b)
Dense(shape=(5, 5), fortran=True)
>>> data.add(a, b, out=data.CSR)
CSR(shape=(5, 5), nnz=25)
```

```python
>>> data.add[data.CSR, data.Dense]
<indirect specialisation (CSR, Dense, Dense) of add>
>>> data.add[data.CSR, data.CSR, data.CSR]
<direct specialisation (CSR, CSR, CSR) of add>
```

#### Basic usage

A `Dispatcher` provides a single mathematical function for _all_ combinations of
types known by `data.to`, regardless of whether the particular specialisation
has been defined for the input data types.  In the first example above, the
operator `data.add` currently only knows two specialisations; it knows how to
add `CSR + CSR -> CSR` and `Dense + Dense -> Dense` directly, but it is still
able to produce the correct result when asked to do `CSR + Dense -> CSR` and
similar.  The type of the output can be, but does not need to be, specified.
The `Dispatcher` will choose a suitable output type if one is not given.

For example, the objects `data.add`, `data.pow` and `data.matmul` are some
examples of dispatchers in the data layer.  Respectively, these have the
signatures

```python
data.add(left: Data, right: Data, scale: complex = 1) -> Data
data.pow(matrix: Data, n: integer) -> Data
data.matmul(left: Data, right: Data) -> Data
```

These are callable functions, so the base use is to call them.

Just like `data.to`, key-lookup syntax can be used to get a single callable
object representing a single specialisation.  The callable object has an
attribute `direct` which is `True` if no type conversions would need to take
place, and `False` is at least one would have to happen.  Just like in the
regular call, you can either specify or not specify the type of the output, but
the types of the inputs must always be given.

```python
>>> data.pow[data.CSR]
<direct specialisation (CSR, CSR) of pow>
>>> data.pow[data.CSR].direct
True
>>> data.pow[data.CSR, data.Dense].direct
False
```

The returned object is callable with the same signature as the dispatcher
(except the `out` keyword argument is no longer there), and requires that the
inputs match the types stated.

#### Adding new specialisations

New specialisations can be added to a pre-existing dispatcher with the
`Dispatcher.add_specialisations` method.  This is very similar in form to
`data.to.add_conversions`; it takes lists of tuples, where the first elements of
the tuple define the types in the specialisation, and the last is the
specialised function itself.

For example, a user might need to multiply `Dense @ CSR` frequently and get a
`Dense` output.  Currently, there is no direct specialisation for this:

```python
>>> data.matmul[Dense, CSR, Dense]
<indirect specialisation (Dense, CSR, Dense) of matmul>
```

The user may then choose to define their own specialisation to handle this case
efficiently:

```python
>>> def matmul_1(left: Dense, right: CSR) -> Dense:
...     # [...]
...     return out
```

They would give this to `data.matmul` by calling

```python
>>> data.matmul.add_specialisations([
...     (Dense, CSR, Dense, matmul_1),
... ])
```

Now we find

```python
>>> data.matmul[Dense, CSR, Dense]
<direct specialisation (Dense, CSR, Dense) of matmul>
```

Additionally, the whole lookup table will be rebuilt taking this new
specialisation into account, which means the indirect specialisation
`matmul(Dense, CSR) -> CSR` will now make use of this new method, because it has
a low conversion weight.


#### Adding new types

Now let's say the user wants to add a new `NewDataType` type all across QuTiP.
The only action they _must_ take is to tell `data.to` about this new type.
Let's say they define it like this:

```python
>>> class NewDataType:
...     # [...]
>>> def new_from_dense(matrix: data.Dense) -> NewDataType:
...     # [...]
>>> def dense_from_new(matrix: NewDataType) -> data.Dense:
...     # [...]
>>> data.to.add_conversions([
...     (NewDataType, data.Dense, new_from_dense),
...     (data.Dense, NewDataType, dense_from_new),
... ])
```

As we saw in the previous section, this is enough to define all conversions in
`data.to`.  What's more, this is _also_ enough to define all operations in the
data layer as well:

```python
>>> data.matmul[NewDataType, data.CSR]
<indirect specialisation (NewDataType, CSR, CSR) of matmul>
```

All of the data layer will now work seamlessly with the new type, even though
this is actually achieved by conversion to and from a known data type.  There
was no need to call anything other than `data.to.add_conversions`.  Internally,
this is achieved by `data.Dispatcher.__init__` storing a reference to itself in
`data.to`, and `data.to` calling `rebuild_lookup` as part of `add_conversions`.

Now the user only needs to add in the specialisations that they actually need
for the bottle-neck parts of their application, and leave the dispatcher to
handle all other minor components by automatic conversion.  As in the previous
subsection, they do this by calling `add_specialisations` on the relevant
operations.


#### Creating a new dispatcher

In most user-defined functions which operate on `Qobj.data` it will be
completely sufficient for them to simply call `data.to(desired_type,
input_data)` on entry to the function, and then they can guarantee that they are
always working with the type of data they support.

However, in some cases they may want to support dispatched operations in the
same way that we do within the library code.  For this reason, the data layer
exports `Dispatcher` as a public symbol.  The minimal amount of work that needs
to be done is to call the initialiser, and then call `add_specialisations`.  For
example, let's say the user has defined two specialisations for their simple new
function `add_square`:

```python
>>> def add_square_csr(left, right):
...     return data.add_csr(left, data.matmul_csr(right, right))
...
>>> def add_square_dense(left, right):
...     return data.add_dense(left, data.matmul_dense(right, right))
...
```

(Ignore for now that this would be better achieved by just using the dispatchers
`data.add` and `data.matmul` directly.)  Now they create the dispatcher simply
by doing

```python
>>> add_square = data.Dispatcher(add_square_csr, inputs=('left', 'right'), name='add_square', out=True)
>>> add_square.add_specialisations([
...     (data.CSR, data.CSR, data.CSR, add_square_csr),
...     (data.Dense, data.Dense, data.Dense, add_square_dense),
... ])
```

This is enough for `Dispatcher` to have extracted the signature and satisfied
all of the specialisations.  Note that the `inputs` argument does not provide
the signature, it tells the dispatcher which arguments are data-layer types it
should dispatch on, e.g. for `data.pow` as defined above `inputs = ('matrix',)`,
but the signature is `(matrix, n) -> out`.  See that the specialisations are now
complete:

```python
>>> add_square
<dispatcher: add_square(left, right)>
>>> add_square[data.Dense, data.CSR, data.CSR]
<indirect specialisation (Dense, CSR, CSR) of add_square>
```

In the initialisation, the function `add_square_csr` is passed as an example
from which `Dispatcher` extracts the call signature, the module name and the
docstring (if it exists).  It is not actually added as a specialisation until
`add_square.add_specialisations` is called afterwards.

If desired, the user can set or override the docstring for the resulting
dispatcher by directly writing to the `__doc__` attribute of the object.  We
_always_ do this within the library.

_Note:_ within the Cython components of the library, we manually construct the
signature and pass it into `Dispatcher.__init__` because Cython-compiled
functions do not embed their signature in a manner in which `inspect.signature`
can extract it (even with the `embedsignature` directive).  We also use this to
cut out some arguments in the call signatures which would not work with the
dispatch mechanism (like `out` parameters).

#### Other features

In combination with `data.to`, this now allows QuTiP to handle _any_ backing
data store for `Qobj`, even if literally zero mathematical functions are defined
for the type.

The `Dispatcher` can operate on a function with any call signature (except ones
which use `*args` or `**kwargs`), even if not all of the arguments are
data-layer types.  At definition, the creator of the `Dispatcher` says which
input arguments are meant to be dispatched on, and whether the output should be
dispatched on, and all other arguments are passed through like normal.

#### Implementation details

The backing specialisations can be found in `Dispatcher._specialisations`, and
the complete lookup table is in `Dispatcher._lookup`.  These are marked as
private, because messing around with them will almost certainly cause the
dispatcher to stop working.

Only one specialisation needs to be defined for a dispatcher to work with _all_
data types known by `data.to`.  We achieve this because `data.to` guarantees
that all possible conversions between data types will exist, so
`data.Dispatcher` can always convert its inputs into those which will match one
of its known specialisations.

Within the initialisation of the data layer, we use a "magic" `_defer` keyword
argument to `add_specialisations` to break a circular dependency.  This is
because the "type" modules `data.csr` and `data.dense` depend on some
mathematical modules (e.g. `add` and `matmul`) to provide the `__add__` and
similar methods on the types.  For ease of development we want the dispatchers
to be defined in the same modules that all the specialisations are (though this
is not at all necessary), but the dispatchers require `data.to` to be populated
with the types before specialisations can be added.  The `_defer` keyword here
just defers the building of the lookup table until an explicit call to
`Dispatcher.rebuild_lookup()`, breaking the cycle.  The user will never need to
do this, because by the time they receive the `Dispatcher` object, `data.to` is
already initialised to a minimum degree.

#### Efficiency notes

The specialisations returned by the `__getitem__` lookups are not significantly
faster than just calling the dispatcher directly, because the bulk of the heavy
lifting is done when `add_specialisations` or `rebuild_lookup` is called.  On
call, the generic signature `(*args, **kwargs)` has to be bound to the actual
signature of the underlying operation, regardless of whether the specialisation
has already been found.  At the Cython level there is short-circuit access to
the call machinery in the specialisations themselves, but this cannot be safely
exposed outside of the `Dispatcher` class itself.
