One of the main advantages of using Cython in the algebraic core of scientific
code is fast, non-bounds-checked access to contiguous memory.  Of course, when
you elide safety-checking, it's not surprising when you start to get segfaults
due to out-of-bounds access and use-after-free bugs in your Cython code.

This post talks a little about why we chose to use raw pointers to access our
memory in the upcoming major version of [QuTiP](http://qutip.org/) rather than
other possible methods, and how I tracked down a couple of memory-safety
bugs in my code which would have been caught had we been using safer
alternatives.

## What good is contiguous memory?

First off: why is it more efficient to use _any_ sort of C-style access rather
than a Python `list`?  The `list` itself is actually represented by contiguous
memory, but due to the way Python manages objects, there is an extra level of
indirection to reach the actual object.  In CPython, a `list` is backed in the C
API by a struct that looks like

```c
typedef struct {
    PyObject_VAR_HEAD
    PyObject **ob_item;
    Py_ssize_t allocated;
} PyListObject;
```

where `PyObject` is the structure used to represent all Python objects (the
list's `PyObject` is hiding in the macro `PyObject_VAR_HEAD`).  The `allocated`
field tells us how much space for elements is allocated in `ob_item`, and
`ob_item` itself is then the list backing.  Ignoring the C API accessors which
we would use if we were writing safe code, we get the struct at element `n` of a
list `PyListObject list` by `*list.ob_item[n]`, which clearly involves two
pointer dereferences (typically we'd actually just need `list.ob_item[n]`
because it's more useful to have the pointer, but that masks the second
dereference to access the underlying data).  Now it's clear that the _data_ we
care about in the list is not contiguous in general, and consequently we're
going to have terrible cache performance for iterated access, not to mention
that when we're dealing with Python objects we also have to take care to handle
ref-counting correctly.

So, it's clear that we'll have hugely better performance dealing with vectors
and matrices of numeric data if we use C-level contiguous memory.  This is what
`numpy` does, and is why it is so crucial for scientific code.  Sometimes,
though, we need more control than what we can achieve with `numpy` arrays,
especially when we have specialised compound operations which `numpy` requires
intermediary copies and allocations to represent.  This is where Cython's power
really shines.

Cython tries to push us towards using
[typed `memoryview` objects][cy-memoryview] that also have
[a Python-compatible view][py-memoryview] and can be constructed from any object
which supports the Python [buffer protocol][py-buffer].  These come with a lot
of nice features like ref-counting, automatic strided access and automatic
bounds-checking (which can be disabled), but unfortunately these come with
initialisation penalties. Also, in our use-cases in [QuTiP](http://qutip.org/)
where we make heavy use of raw BLAS and LAPACK, we want to guarantee that 2D
data is backed by contiguous memory, but may be in either Fortran or C order.
Now we have to use generic strides which disallows some optimisations and
loop-unrolling, unless we use the awkward `&memoryview[0]` construction to
"trick" Cython into giving us the raw pointer, which rather defeats the purpose
of using the `memoryview` in the first place.

Memory ref-counting is not so much of a concern for us here, because our
pointers and allocations are either all made and released within a single
function's scope, or are bound to a Python object where we can use Cython's
`__dealloc__` method to effect the `free`.  Within a single function, we can use
the idiom

```cython
cdef double f(double *x, size_t n) except -1:
    cdef double out=0
    cdef double *temporary = <double> PyMem_Malloc(n * sizeof(double))
    if temporary == NULL:
        raise MemoryError
    try:
        # Do some things which may throw Python exceptions.
        # ...
        return out
    finally:
        PyMem_Free(temporary)
```

such that `temporary` is always freed, whether the function returns normally
from anywhere in the `try` block or throws an exception.  Of course if there's
no operations which could possible throw an exception, which is quite common in
`cdef` functions which release the GIL, we _can_ skip the `try`/`finally` step.
It is frequently still useful, though, if the function has multiple possible
return locations; Cython does not allow us to use the C `goto cleanup` idiom
directly, but it will transfer these `finally` blocks into very similar code.

So, all-in we get lots of speed and library benefits from using raw pointers,
and we don't really sacrifice very much as our data types make guarantees about
the strides and types of the data at initialisation time.  The one place we _do_
lose out on, though, is the possibility of run-time bounds-checking, as Cython's
`boundscheck` directive naturally cannot run on raw pointers, which do not carry
size information with them.



## Debugging without Cython directives

### Address access violations

When running our test suite, in some cases I'd find a segfault _after_ `pytest`
had finished running and all the results had been printed, but before control
returned to `bash`, with a simple "Segmentation fault".  Since Python 3.3, we
can use the [`faulthandler` module][py-faulthandler] to ensure we get the stack
trace dumped even in cases of `SIGFPE`, `SIGSEGV` and a few others.  To enable
it, we can either set the `PYTHONFAULTHANDLER` environment variable, or run
`python` with the `-Xfaulthandler` option.  We can't use the `pytest` "binary"
with the latter option because it doesn't pass on unknown options to the Python
interpreter, but we can use the older module-call syntax as in

```bash
python -Xfaulthandler -mpytest [pytest arguments]
```

Typically doing this would give us a proper traceback, albeit without the code
context that Python usually would (running in reduced mode, it has to produce
the traceback without acquiring new resources like file handles).  In this case,
however, it's not so useful:

```text
Fatal Python error: Segmentation fault

Current thread 0x00000001113635c0 (most recent call first):
<no Python frame>
Segmentation fault: 11
```

Now, this error coming outside any Python frames makes me suspect that the error
comes in a deallocation routine.  I'm reasonably certain that there aren't any
double-free errors going on here, because our memory management (at least at
this early stage) isn't so complicated, and the test suite allocates and
deallocates several hundreds of thousands of these objects.  Instead, it's much
more likely that I've made a mistake in one of the mathematical algorithms and
caused some out-of-bounds access.

If we were using Cython `memoryview` types, the next step would be to turn on
the `boundscheck` directive.  With raw pointers, though, that's not an option,
so we have to go rather more low-level.  Google have released several
"sanitizers" for C/C++ code, whose
[home page is on GitHub](https://github.com/google/sanitizers) and can be used
with both `clang` and `gcc`.  Right now I'm mostly interested in turning on
AddressSanitizer, which I do with the `-fsanitize=address` flag at compile and
link times.  It is enough to do this just for Cython extension modules; I don't
have to recompile Python with it.

By default, `gcc` will link to the corresponding `libasan` dynamically, and my
`gcc` is in a non-standard place, so I also have to set the environment variable

```bash
DYLD_INSERT_LIBRARIES=/usr/local/opt/gcc/lib/gcc/9/libasan.5.dylib
```

when running anything which will use the extensions afterwards.  There is the
`-static-libasan` flag, though my `g++` was complaining about it, and I didn't
investigate that much further.

This now causes the access violation to be reported at the point it occurs, and
gives us a _much_ more useful traceback:

```text
==42485==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x604000007578 at pc 0x00012172bed5 bp 0x7ffee5c2e0a0 sp 0x7ffee5c2e098
READ of size 4 at 0x604000007578 thread T0
    #0 0x12172bed4 in __pyx_f_5qutip_4core_4data_7reshape_reshape_csr(__pyx_obj_5qutip_4core_4data_3csr_CSR*, int, int, int) reshape.cpp:2614

0x604000007578 is located 0 bytes to the right of 40-byte region [0x604000007550,0x604000007578)
allocated by thread T0 here:
    #0 0x10a4b081f in wrap_malloc (libasan.5.dylib:x86_64+0x7b81f)
    #1 0x11175c091 in PyDataMem_NEW (_multiarray_umath.cpython-38-darwin.so:x86_64+0x2091)
    #2 0x1215e44a9 in __pyx_f_5qutip_4core_4data_3csr_empty(int, int, int, int) csr.cpp:10101

SUMMARY: AddressSanitizer: heap-buffer-overflow reshape.cpp:2614 in __pyx_f_5qutip_4core_4data_7reshape_reshape_csr(__pyx_obj_5qutip_4core_4data_3csr_CSR*, int, int, int)
Shadow bytes around the buggy address:
  0x1c0800000e50: fa fa fd fd fd fd fd fd fa fa fd fd fd fd fd fd
  0x1c0800000e60: fa fa fd fd fd fd fd fd fa fa fd fd fd fd fd fd
  0x1c0800000e70: fa fa 00 00 00 00 00 00 fa fa fd fd fd fd fd fd
  0x1c0800000e80: fa fa fd fd fd fd fd fd fa fa 00 00 00 00 00 00
  0x1c0800000e90: fa fa 00 00 00 00 04 fa fa fa 00 00 00 00 04 fa
=>0x1c0800000ea0: fa fa 00 00 00 00 04 fa fa fa 00 00 00 00 00[fa]
  0x1c0800000eb0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1c0800000ec0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1c0800000ed0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1c0800000ee0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1c0800000ef0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
  Shadow gap:              cc
==42485==ABORTING
Fatal Python error: Aborted

Current thread 0x000000011951a5c0 (most recent call first):
  File "/Users/jake/code/qutip/qutip/qutip/core/superoperator.py", line 277 in stack_columns
  File "/Users/jake/code/qutip/qutip/qutip/core/superoperator.py", line 246 in operator_to_vector
  [...]
```

In the real output, the memory dump and legend are colour-coded as well.  We can
now see straight away which function is causing the problem---at Python level
it's in `qutip.core.superoperator.stack_columns`, which has called a Cython
function `__pyx_f_5qutip_4core_4data_7reshape_reshape_csr` whose name unmangles
to `qutip.core.data.reshape.reshape_csr`.  It also tells us that it's a heap
buffer overflow, which suggests a slight out-of-bounds access to `malloc`ed
memory.

Now it's just a case of spotting the error in that function.  Here, it's a
fairly classic C blunder:

```cython
cpdef CSR reshape_csr(CSR matrix, idxint n_rows_out, idxint n_cols_out):
    cdef idxint nnz = csr.nnz(matrix)
    cdef CSR out = csr.empty(n_rows_out, n_cols_out, nnz)
    memcpy(out.data, matrix.data, nnz*sizeof(double complex))
    memset(out.row_index, 0, (n_rows_out + 1) * sizeof(idxint))
    for row_in in range(n_rows_in):
        # [...] calculations omitted
    for row_out in range(n_rows_out + 1):
        out.row_index[row_out + 1] += out.row_index[row_out]
    return out
```

The pointer `out.row_index` _is_ allocated space for `n_rows_out + 1` elements,
which is why I originally wrote the last `for` loop with that range, but of
course we actually access two elements at once, so there's an off-by-one error.
Fixing this removes the segfaults, and one we go!


### Zero-division errors

Since we're at it, we can also turn on a few more sanitizers to see if I've
introduced any more possible bugs (spoiler alert: I have).  In particular, I
also turn on `-fsanitize=undefined` and `-fsanitize=float-divide-by-zero`.  The
latter is not covered by "undefined behaviour", because the expression `1./0.`
is used in real code to obtain `NaN` or `inf` values, but I know that we don't
do that, so there's no worries there.

As a small side note: if you're using `pytest`, it will intercept access to the
`stdout` and `stderr` file streams by the testee process, including the dump by
UBSan/ASan.  You should disable this by using the `-s` option, as in
`pytest -s`, when trying to use them.

The new error I find here doesn't give quite as useful a traceback at the C
level as the previous one, but we still get the Python traceback and a
line number in the Cython-generated C++ file:

```text
qutip/core/data/permute.cpp:6465:94: runtime error: division by zero
AddressSanitizer:DEADLYSIGNAL
=================================================================
==43176==ERROR: AddressSanitizer: FPE on unknown address 0x7fff679372c2 (pc 0x7fff679372c2 bp 0x000112649280 sp 0x000112649248 T0)
    #0 0x7fff679372c1 in __pthread_kill (libsystem_kernel.dylib:x86_64+0x72c1)

==43176==Register values:
rax = 0x0000000000000000  rbx = 0x0000000117edc5c0  rcx = 0x0000000112649248  rdx = 0x0000000000000000
rdi = 0x0000000000000307  rsi = 0x0000000000000008  rbp = 0x0000000112649280  rsp = 0x0000000112649248
 r8 = 0x0000000112649748   r9 = 0x1406b3dc627c30db  r10 = 0x0000000000000000  r11 = 0x0000000000000287
r12 = 0x0000000000000307  r13 = 0x000000011464ab80  r14 = 0x0000000000000008  r15 = 0x000000000000002d
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: FPE (libsystem_kernel.dylib:x86_64+0x72c1) in __pthread_kill
==43176==ABORTING
Fatal Python error: Aborted

Current thread 0x0000000117edc5c0 (most recent call first):
  File "/Users/jake/code/qutip/qutip/qutip/core/qobj.py", line 1133 in permute
  File "/Users/jake/code/qutip/qutip/qutip/qip/operations/gates.py", line 1389 in expand_operator
  [...]
```

Cython helpfully annotates its output files with comments telling us which
Python lines each block corresponds to, so it's easy to track it down to here:

```cython
cpdef CSR dimensions_csr(CSR matrix, object dimensions, object order):
    cdef _Indexer index = _Indexer(matrix, dimensions, order)
    cdef idxint[:] permutation
    # ...
    if (matrix.shape[0] * matrix.shape[1]) // csr.nnz(matrix) > 0:
        permutation = index.all()
        return _indices_csr_full(matrix, permutation, permutation)
    return _dimensions_csr_sparse(matrix, index)
```

It turns out in my error checking at the start of the function, I'd simply
missed out the line that checked that `csr.nnz(matrix)` was non-zero.  This bug
actually affected a couple of lines in the same module, so I was able to fix a
few possible errors in the same breath.

This particular class of error also would have been caught by setting the Cython
directive `cdivision=False`, but the sanitizers caught it before I'd even
thought to look for it!

----

Using raw pointers doesn't have to mean that we lose access to all the heavy
error checking we're used to with Python.  Naturally these methods are a bit
less fool-proof than Python's permanent bounds-checking and exception
propagation, but they're an exceptionally useful tool that we can compile in
only on debug builds, and omit from release builds.


[cy-memoryview]: https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html
[py-memoryview]: https://docs.python.org/3/library/stdtypes.html#memoryview
[py-buffer]: https://www.python.org/dev/peps/pep-3118/
[py-faulthandler]: https://docs.python.org/3/library/faulthandler.html
