In [QuTiP][qutip] we have some optional [OpenMP][omp] components, which can be
used if the C extensions are built with OpenMP support at compile time.
Typically this should be achievable just by adding the `-fopenmp` flag at
compile and link time, but unfortunately the `llvm` `clang` distribution that
Apple ship with macOS is not built with OpenMP support.

---

We can solve this by installing a fully-functional form of `gcc` from
[Homebrew][homebrew] (or any other method).  My current `gcc` is version 9.3,
which is installed in prefix `/usr/local/opt/gcc`.  This now allows the
`-fopenmp` flag and can compile simple OpenMP-enabled executables, but
dynamically linked libraries will fail at runtime, failing to find various
symbols such as `_GOMP_parallel`.  This is because `gcc` will call Apple's
linker, which obviously will not know about the additional libraries.  We point
`ld` to include the correct runtime directories with the `-rpath` linker
directive and link the `gomp` library, setting for example

```bash
$ LDFLAGS="-lgomp -Wl,-rpath,${GCCPREFIX}/lib/gcc/9"
```

where `${GCCPREFIX}` is as defined above, and the version at the end will change
depending on your `gcc` version.


[qutip]: http://qutip.org
[omp]: https://www.openmp.org
[homebrew]: https://brew.sh
