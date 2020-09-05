This post is the final permalink for the work I've done for [QuTiP][qutip] in
the [Google Summer of Code 2020][gsoc].  My mentors have been Alex Pitchford,
Eric Giguère and Nathan Shammah, and QuTiP is under the [numFOCUS][numfocus]
umbrella.

The main aim of the project was to make `Qobj`, the primary data type in QuTiP,
able to use both sparse and dense representations of matrices and have them
interoperate seamlessly.  This was a huge undertaking that had far-reaching
implications all across the library, but we have now succeeded.  There is still
plenty of work to be done in additional development documentation and on
sanding out the edges to improve the UX, but we are moving towards a public
beta of a major version update next year.

[qutip]: http://qutip.org/
[gsoc]: https://summerofcode.withgoogle.com/
[numfocus]: https://numfocus.org/


## Background

The primary class in QuTiP is `Qobj`, which represents all quantum objects.
Historically, `Qobj` has always used a compressed-sparse-row (CSR) format to
store its backing data, a design decision stemming from the library's original
aim of being a drop-in Python replacement for the [Quantum Optics Toolbox for
MATLAB][qomatlab] ([GitHub source mirror][qomatlab-gh]).  Sparse matrices are
typically an excellent choice for quantum optics, which frequently deals with
large systems with very few allowed transitions, but incur significant
computational and memory overheads when dealing with small systems, or very
dense matrices such as propagators.

As QuTiP has evolved, and as quantum computation and the circuit model have
become more prevalent with the scientific community moving into the NISQ era,
the cases where dense matrices are preferred have become much more common.
Ideally, we want to be able to use the best matrix representation for every
different object, and have this be completely seamless to the user within
normal execution.

In Julia, [QuantumOptics.jl][qo-jl] does something similar using Julia's
built-in multiple-dispatch capabilities and type traits, but the main bulk of
its support stems from stronger interoperability between the `Matrix` and
`SparseMatrix` standard-library types in that language.  In Python,
`scipy.sparse` arrays and `numpy.ndarray` _do_ interoperate well for the most
part, but due to how generic it is required to be `scipy.sparse.csr_matrix` is
too slow for our use-case.  The backing data store of `Qobj` was replaced in
late 2016 by Paul Nation, one of the original developers, with a modified
version of `csr_matrix` which elided a lot of run-time checks that caused most
of the slowdown (see: [qutip#577][gh-577], [qutip#595][gh-595] and
[qutip#609][gh-609]).

As the library has developed, more and more low-level quantum-specific
functions have been written in [Cython][cython], always assuming the backing
data store is the new `fast_csr_matrix` type, along with all its type checks.
The more of these functions we have in the library, the harder it is to
introduce a new data type; as soon as we strayed away from pure NumPy and SciPy
functions, we lost the "free" interoperability between dense and sparse
representations, and to add a new type we would have had to contend with
exponential scaling of the number of functions we would have to write to
support everything.

The aim of this project was to introduce full interoperability of different
matrix representations, not necessarily limited to a dense matrix and just one
sparse format, without tripling the size of the library and requiring every new
function to have several versions.

You can also read my [first blog post][first-post] introducing the topic, and
[my original GSoC proposal][proposal] in PDF format.  All my intermediary blog
posts can be found on this site under the [GSoC tag](${tag_gsoc}), most of
which are design drafts and the first passes at a lot of documentation.

[qomatlab]: https://qo.phy.auckland.ac.nz/toolbox/
[qomatlab-gh]: https://github.com/jevonlongdell/qotoolbox
[qo-jl]: https://qojulia.org/
[gh-577]: https://github.com/qutip/qutip/pull/577
[gh-595]: https://github.com/qutip/qutip/pull/595
[gh-609]: https://github.com/qutip/qutip/pull/609
[cython]: https://cython.org/
[first-post]: ${article_b6b144}
[proposal]: ${article_b6b144}/proposal.pdf


## Project pull requests

The main bulk of my project is done now, separated across a few different pull
requests.

### Isolating `qutip.core` ([#1282][gh-1282])

I isolated the core functionality of QuTiP into `qutip.core`, a physical split
in the file storage, but mostly one which is completely transparent to the
user.  This was mostly for our internal organisation, and to help break us out
of a huge circular dependency issue.

This was where I gained a lot of knowledge on packaging and distribution Cython
extension modules along with Python code, and a few things I'd rather not have
needed to learn about [getting OpenMP working on macOS](${article_fb9b1c}).

[gh-1282]: https://github.com/qutip/qutip/pull/1282


### Adding the `Dense` and `CSR` types ([#1296][gh-1296])

This put in a lot of the implementation of these types, although `CSR` had more
attention, as a lot of code could be ported from the old versions.

We made a decision _not_ to use `numpy.ndarray` or `scipy.sparse.csr_matrix` as
the backing stores for `Qobj`; `csr_matrix` had already been replaced by the
custom `fast_csr_matrix` which was not ideal due to its use of private SciPy
functions whose API is not stable, and with the amount of Python--C interchange
that needed to happen, it was much more efficient to have the data types be C
extension types defined in Cython.  These "first-class" data types are `Dense`
and `CSR`, though we also allow user-defined types which may be pure Python.

I especially like the idea behind the test generation for the mathematical
operations although I am not sure I pulled it off as neatly as it could have
been done.  See in particular the [`test_mathematics.py` file][1296-test_mathematics].

When writing these types, I made the type they use to represent indices a
`typedef` at the top layer of the code.  In theory, this allows the user to
select at compile-time (assuming they are compiling it for themselves rather
than using a pre-built package) the size of integer they want to use
internally, fulfilling one of the minor project aims.

[gh-1296]: https://github.com/qutip/qutip/pull/1296
[1296-test_mathematics]: https://github.com/qutip/qutip/blob/58cd388c0456d6680d2978f769f0876cff209758/qutip/tests/core/data/test_mathematics.py


### Replacing `fast_csr_matrix` with `CSR` in `Qobj` ([#1332][gh-1332])

This was by far the most fiddly and longest part of the project, despite
being technically very simple.  The aim was simply to switch over to the new
`CSR` type from the old `fast_csr_matrix`, and using this opportunity to find
every place in the code where we depended on the type specifically being the
SciPy-like type.

It turns out that there were a _lot_ of places which assumed that `Qobj.data`
was in this format, and it took a lot of work to migrate everything to the new
system, particularly in the "solvers" (e.g. of the Schrödinger equation
`sesolve`, the Lindbladian master equation `mesolve` and so on) which are
naturally very low level.

As part of the switch-over, I made fairly heavy optimisations to the `Qobj`
constructor, including ensuring that all library code passed it all the
information that they knew at the time of the call, rather than letting it
infer it later.  This had large speed implications; the runtime for matrix
multiplication of two simple qubits went down from about 100µs to 5µs.

The algorithm for multiplying CSR matrices with dense vectors in QuTiP has been
written in C++ for some time now, to take advantage of SIMD vectorisations that
compilers typically would not apply as part of the build process.  This posed a
problem for the variable-width index type used in `CSR`, as the C++ was not
aware of the `typedef` made in the Cython code.  I solved this by templating
out the C++ code so that function was always generated with the correct integer
width.

[gh-1332]: https://github.com/qutip/qutip/pull/1332


### Creating the multiple-dispatch mechanism ([#1338][gh-1338])

This was the most technical aspect of the project.  We needed a way to have
simple mathematical functions which could take any data-layer object and
perform the requested operation on them, without requiring us as the
maintainers to have to write an exponential number of specialisations to
support every possible combination of inputs and output type.

I achieved this with two flagship objects which together primarily make up the
"data layer".  These are `data.to` and `data.Dispatcher`; the short version is
that the dispatcher binds the inputs, extracts the data-layer types present,
and then chooses the "closest" specialisation of its function.  If there is no
exact specialisation, then it uses the conversion function `data.to` to convert
the input into a matching type, so it can perform the operation.  There is far
more information in [the pull request itself][gh-1338].

`data.to` provides conversions between all data types which make up the data
layer.  Registering a type with `data.to` is sufficient to add it to the data
layer, where it can then be used all across QuTiP in every operation.
Conversion functions are specified here with the type signature `'A -> 'B`,
where `'A` and `'B` are generic data-layer types.  We then consider the types
themselves to form the vertices of a graph, while the conversion
specialisations are the _directed_ edges.  The problem of converting `'F -> 'G`
for arbitrary known types is now a graph traversal one; at initialisation (and
at specialisation or type addition) we build an entire lookup table with the
shortest path from every node to every other node, sacrificing memory for
run-time speed.  We allow users to define weights for different conversions,
effectively specifying their preferred types.

`data.Dispatcher` has a Cython reimplementation of the Python parameter
resolution process, which intercepts the arguments that need to be dispatched
on.  It then uses a hash-table lookup to find the "closest" specialisation for
the given function that it actually knows.  For example, `matmul` has
specialisations for `(CSR, CSR) -> CSR`, `(Dense, Dense) -> Dense` and `(CSR,
Dense) -> Dense`, but not for the other five possible combinations of these two
types.  If such a specialisation is required, `Dispatcher` uses `data.to` to
convert the arguments to the nearest match (where the conversion weight and
possible specialisation weight make up the "distance").  Since this is done by
hash-table lookup, this is an $`\mathcal O(n)`$ lookup, where $`n`$ is the
number of arguments to be dispatched on.  There is no computational dependence
on the number of known types at run-time, although there is when we build the
table.

[gh-1338]: https://github.com/qutip/qutip/pull/1338


### Activating the dispatch across QuTiP ([#1351][gh-1351])

Finally, the last step was simply to activate the dispatchers all across QuTiP.
After the heavy lifting was done breaking the dependence on `scipy` in
[#1332][gh-1332], this was a simple process.  The end result is that `Qobj` can
now use any backing data store known by `data.to`.

There is still quite a lot of roughness at this stage that I intend to keep
working on well after the summer of code is ended, but formally this PR
completed all the aims of my original proposal.

[gh-1351]: https://github.com/qutip/qutip/pull/1351

## Other work on QuTiP

At the same time, I have been quite involved in other aspects of QuTiP,
including helping out users in the [discussion boards][qutip-group].

In July, I was involved in the release of QuTiP 4.5.2.  This was mostly
triggered by the release of SciPy 1.5; without the new data-layer types that I
worked on, the 4.x branch relied in part on private `scipy` functions that were
renamed in the 1.5 release.  I wrote PRs [1298][gh-1298],
[1301][gh-1301] and [1302][gh-1302] so we could make a new release
(since _all_ 4.x QuTiP releases were incompatible with SciPy 1.5).

I have also been taking on more work to do with tidying up the distribution,
building and testing processes ([1303][gh-1303], [1312][gh-1312] and
[1347][gh-1347]), something I had already been partially involved in before
beginning the summer of code.  I have also sped up several algorithms and
handled edge cases better in a few places ([1306][gh-1306], [1307][gh-1307] and
[1352][gh-1352]), mostly where testing the new data layer turned up possible
problems that were present in the 4.x branch.

[qutip-group]: https://groups.google.com/g/qutip
[gh-1298]: https://github.com/qutip/qutip/pull/1298
[gh-1301]: https://github.com/qutip/qutip/pull/1301
[gh-1302]: https://github.com/qutip/qutip/pull/1302
[gh-1303]: https://github.com/qutip/qutip/pull/1303
[gh-1306]: https://github.com/qutip/qutip/pull/1306
[gh-1307]: https://github.com/qutip/qutip/pull/1307
[gh-1312]: https://github.com/qutip/qutip/pull/1312
[gh-1347]: https://github.com/qutip/qutip/pull/1347
[gh-1352]: https://github.com/qutip/qutip/pull/1352


## Still to do

I still have an list of things I want to achieve before we release QuTiP 5.0 to
the public.  There are several sparse algorithms that I identified as places
for improvement (`add_csr` and `matmul_csr` being two major ones), and there
are more tests that need to be written.  We have historically been less than
perfect with regards to our testing in QuTiP, which is something I would like
to change.

Most relevant to the project, there are also several UX concerns that I would
prefer to address before the release.  Currently it is simple to require
certain output _types_, but it is complicated to force the `Dispatcher` to use
a particular _specialisation_.  In various algorithms, this is a notable
omission; for example in especially large sparse matrices, it may not be
possible to use a dense eigenvalue solver, even though in regular usage the
dense method is preferred.  At present, we have not fully worked out the
details of what this API will look like.


## Final thoughts

I really have enjoyed working full time as a software engineer as part of the
summer of code programme.  I didn't know whether I would enjoy my hobby when
working on it as a job, so I am glad to have this experience before the end of
my PhD.

My two primary mentors (Eric Giguère and Alex Pitchford) have been excellent;
very responsive, eager to talk about technical details and offer advice on API
design and user experience.  Nathan Shammah organised several "outreach"-type
meetings with the rest of the QuTiP team to keep us all working together, and
aware of what each other was doing, which was also lovely.

I am fairly sure I will keep working in open source, and on QuTiP in particular
going forwards; I actually started before I was aware of Google Summer of Code,
so I am very hopeful that I will continue through the 5.0 release cycle and
beyond!

Thank you to everyone involved!
