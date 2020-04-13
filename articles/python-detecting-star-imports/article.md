Star (or wildcard) imports are one of the methods for importing libraries in
Python, and although they are generally discouraged, they are rather prevalent
in a lot of notebook-style scientific code.  Within a package being imported,
there is no _official_ way of knowing whether this is by a star import, but
since Python allows overriding just about everything, we can detect slight
differences in the methods and inject arbitrary code if the wildcard is used.

In [QuTiP][qutip], we currently suffer from long import times and want to
move to a `scipy`-like style where fewer symbols are in the global package
namespace, and submodules are only imported if explicitly requested.  We want
to issue a warning to people currently using the `from qutip import *` syntax,
because the number of symbols available to them will soon decrease.


## The import system

Whenever a package or module is used in Python, it first has to be imported
into the current scope.  The `import` statement can take a few different forms,
depending on how many names are to be imported the package, and whether they
should be placed in the module's namespace or the global one:

 - `import module`:
        make all names accessible under the module name `module`, like
        `module.name1`;
 - `from module import (name1, name2)`:
        make only `name1` and `name2` visible in the global scope---the module
        is imported and added to `sys.modules`, but the module name is not
        added to the scope;
 - `from module import *`:
        make "all" names in the module visible in the current global scope.
        The module name is not added to the scope.

The first two are common and clean ways to bring in additional functionality,
but the latter is [rather][star1] [more][star2] [contentious][star3] because it
will typically import many names into the global namespace which could
overwrite existing definitions or built-ins.  It also in general means that
IDEs and linters will not be able to detect which package a given symbol has
come from, or if it is even defined at all.

For all methods, the `__init__.py` (for a package) or `[module].py` (for a
module) is run first in an empty scope to initialise the module and execute all
the code contained within.  If a wildcard import is used, then all names in the
module scope are added to the outer scope, unless they begin with an
underscore.

The package can control wildcard imports a little bit, to prevent _all_ of the
names being imported.  This is the `__all__` object, to be defined at module
scope.  For example, a module `build` may provide the functions `read_code`,
`write_code`, and `compile`.  Now `compile` is a [Python built-in][compile], so
this should not be exported unless the user specifically asks for it to shadow
the default definition.  To achieve this, the `__init__.py` looks like

```python
__all__ = ['read_code', 'write_code']

def read_code(*args, **kwargs):
    pass

def write_code(*args, **kwargs):
    pass

def compile(*args, **kwargs):
    pass
```

Now `import build` will allow `build.read_code`, `build.write_code` and
`build.compile` to be used, since all those names exist in the inner scope.
However, `from build import *` will only give access to `read_code` and
`write_code`, because the import system was told that that is "`__all__`" there
is.  In pseudo-code the wildcard import is very similar to

```python
scope = globals()
import build
for name in build.__all__:
    scope[name] = getattr(build, name)
del build
```

For detection purposes, it is important that `__all__` is only accessed in the
case of the wildcard import, but it is always created.


## Detecting the wildcard import

`__all__` is a sequence of strings, but Python's dynamic typing means that it
does not _have_ to be a list, it just has to behave like one.  This means that
we can make an object which behaves like a list, but with side-effects when
a caller attempts to iterate through it.  It is not enough to pass a warning on
creation, because then all imports will see it.

An example `__init__.py` file then looks like:

```python
import warnings as _warnings
from qutip.core import Qobj, sesolve
from qutip import control

class _StarDetector(list):
    def __iter__(self):
        _warnings.warn("QuTiP 5 will require explicit importing of submodules",
                       FutureWarning)
        return super().__iter__()

__all__ = _StarDetector(['Qobj', 'sesolve', 'control'])

del _StarDetector
```

The wrapper class `_StarDetector` inherits from `list`, so its behaviour is
identical.  It overrides the `__iter__` method, but only to insert the code to
be run; it then calls `list.__iter__` via `super` so that the normal workings
are not interrupted:

```python
>>> import qutip
>>> dir(qutip)
['Qobj', '__all__', ..., '_warnings', 'control', 'sesolve']
>>> from qutip import Qobj
>>>
```

The star import triggers the warning, however:

```python
>>> from qutip import *
.../qutip/__init__.py:8: FutureWarning: QuTiP 5 will require explicit importing of submodules.
  FutureWarning)
```

There are a couple of limitations to this:

 - it will only work in a package, not a module;
 - the iteration is done _after_ the `__init__.py` file has been executed in
   full, so it cannot be used to modify the importing process itself;
 - `DeprecationWarning` will be hidden by default loggers, as the import
   system does not count as being &ldquo;code in `__main__`&rdquo;---hence
   `FutureWarning` in use here;
 - somebody importing the module normally and accessing `__all__` will still
   see the warning.

This is rather hacky, and a linter may well (correctly!) shout at you.  Still,
due to Python's dynamic typing, there _is_ a way to detect star imports, even
if it is not really the best practice!

[qutip]: http://qutip.org
[star1]: https://medium.com/@s16h/importing-star-in-python-88fe9e8bd4d2
[star2]: https://www.flake8rules.com/rules/F403.html
[star3]: https://stackoverflow.com/questions/2386714/why-is-import-bad
[compile]: https://docs.python.org/3/library/functions.html#compile
