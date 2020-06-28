Debuggers are complicated, especially ones that attach to compiled executables.
In Python `pdb` runs inside the interpreter, so it does not need to control
other processes, but this will not work once we have [Cython][cython]-compiled
components (or other C extensions) in our Python programmes.  Unfortunately,
Cython offers us plenty of opportunities to shoot ourselves in the foot, and it
is more likely we will need to debug use-after-free, double-free or other nasty
segfault situations.

Cython does come with a debugger, which is more properly a set of Python
extensions to [`gdb`, the GNU debugger][gdb].  Macs come with `lldb` installed
and functional, but sadly getting `gdb` running is a bit tricky.  At the time
of writing, I have macOS 10.14 Mojave, the current version of `gdb` is
9.2, and Cython is 0.29.14.  Further, the Cython extensions require Python 2.7,
but I need to be able to debug Python 3 programmes since it's the only
supported version of Python.

As of right now, I do not have a fully working debugger, but hopefully I will
update this post after rebuilding `gdb` with some minor patches.

## Building the debugger

`gdb` is available on [Homebrew][homebrew], but the Homebrew version is built
against the most recent version of Python (currently 3.8).  This is no good for
us, so we have to build from source.

I downloaded the latest source file `gdb-9.2.tar.gz` and unzipped it into
`~/code/gdb-9.2`.

```bash
$ tar xf ~/Downloads/gdb-9.2.tar.gz ~/code/gdb-9.2
```

This actually gives us a subset of GNU `binutils`, of which
`gdb` is only one subfolder in an `autotools`-managed build process.   The root
`README` tells us to look in `gdb/README` which itemises the options to
`gdb/configure`, and in turn the root `configure`.

The only option I needed to set was to compile `gdb` with Python 2.7 support.
Since this version of Python will also need to see Cython, I do not want to
rely on my system `python` (which happens to be 2.7), so I set it up in a
`conda` virtual environment:

```bash
$ conda create -n cython-debug python=2.7 cython
$ conda activate cython-debug
```

This is not the `conda` environment that I will have active when I am using the
debugger, it is only necessary to ensure that `gdb` finds the correct version
of Python, even when my default is Python 3.  To install, `gdb` requires us not
to be in the root source directory, so I create a subdirectory `build` and run
the configuration process from there.  I still have my `cython-debug`
environment active, so that `python2.7` is from there.

```bash
$ mkdir ~/code/gdb-9.2/build
$ cd ~/code/gdb-9.2/build
$ ~/code/gdb-9.2/configure --with-python=$(which python2.7)
$ make
$ sudo make install
```

I could have used the `--prefix` option to `configure` to set the install
directory to somewhere other than `/usr/local` (and hence avoided the
`sudo`), but I didn't think this was too important for me.  Running `gdb`
directly from the build directory, without doing the installation, caused it to
complain

```
Could not load the Python gdb module from `/usr/local/share/gdb/python'.
Limited Python support is available from the _gdb module.
Suggest passing --data-directory=/path/to/gdb/data-directory.
```

The search location `/usr/local/share/gdb/python` makes it clear that the
installation is important.

At this point `gdb` exists on the system path, and the `conda` environment we
created can now be safely ignored---as long as it exists, we can `conda
deactivate` and move to whatever environment we like, and `gdb` will still run
its Python components without complaint.


## Signing the debugger

We can test the debugger with a simple C programme, for example

```c
#include <stdio.h>

int f(int x)
{
    return x * x;
}

int main(int argc, const char **argv)
{
    int y = f(3);
    printf("hello, world: %d, %d\n", y, f(6));
    return 0;
}
```

I have compiled this with debugging symbols `gcc -g` to `~/code/ctest/main`.
If I try to run the debugger now, I get a kernel error

```
$ gdb ~/code/ctest/main
(gdb) run
Starting program: /Users/jake/code/ctest/main
Unable to find Mach task port for process-id 52235: (os/kern) failure (0x5).
 (please check gdb is codesigned - see taskgated(8))
```

`gdb` tells us that it needs to be "code-signed" to be granted the
authorisations it needs to function, which has been necessary since Leopard (OS
X 10.5).  First we have to [create a code-signing certificate][gnu-codesign],
and ensure that it's in the System keychain.  I kept getting an "Unknown error"
when trying to create it there directly in the wizard, but I created `gdb-cert`
in the Login keychain, then just moved it over.

Further, since Mojave (OS X 10.14), we have to grant `gdb` the
`com.apple.security.cs.debugger` entitlement.  The system `lldb` is a thin
pass-through to its debug server distributed within Xcode, so we can extract
the necessary entitlements from there:

```
$ codesign -d --entitlements :gdb-entitlements.xml /Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/debugserver
Executable=/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Versions/A/Resources/debugserver
```

The file `gdb-entitlements.xml` now looks like

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.debugger</key>
    <true/>
</dict>
</plist>
```

We code-sign the `gdb` executable with

```
$ codesign --entitlements gdb-entitlements.xml -fs gdb-cert $(which gdb)
```

where the `-f` option causes `codesign` to override any signatures that may
already exist.  This operation may need to be run as root if the `gdb`
executable is somewhere that isn't writeable.

If you have already run `gdb` before code-signing, you may need to reload
`taskgated` to clear the authorisation cache.  Since it's a required kernel
process, we can just kill it: `sudo pkill taskgated`.


## Internal debugger issues

In theory, `gdb` should be working now.  I can run `gdb ~/code/ctest/main`, and
am greeted by a functioning interpreter:

```
Reading symbols from main...
Reading symbols from /Users/jake/code/ctest/main.dSYM/Contents/Resources/DWARF/main...
(gdb) r
Starting program: /Users/jake/code/ctest/main
[New Thread 0x1903 of process 5530]
[New Thread 0x1b03 of process 5530]
hello, world: 9, 36
[Inferior 1 (process 5530) exited normally]
(gdb) q
```

It is odd to me that two threads are spawned for a single-threaded programme,
but it still ran.  A larger problem is that occasionally on issuing the `run`
command, `gdb` just completely hangs after only spawning the first thread.  To
kill it, `ctrl-C` isn't sufficient, but suspending it with `ctrl-Z` and
following it with `kill -9` are.

More pressing is that trying to load debugging symbols from a file causes an
internal `gdb` error:

```
$ gdb
(gdb) file main
Reading symbols from main...
Reading symbols from /Users/jake/code/ctest/main.dSYM/Contents/Resources/DWARF/main...
../../gdb/inferior.c:283: internal-error: inferior* find_inferior_pid(int): Assertion `pid != 0' failed.
A problem internal to GDB has been detected,
further debugging may prove unreliable.
Quit this debugging session? (y or n) n

This is a bug, please report it.  For instructions, see:
<http://www.gnu.org/software/gdb/bugs/>.

../../gdb/inferior.c:283: internal-error: inferior* find_inferior_pid(int): Assertion `pid != 0' failed.
A problem internal to GDB has been detected,
further debugging may prove unreliable.
Create a core file of GDB? (y or n) n
Command aborted.
(gdb) r
Starting program: /Users/jake/code/ctest/main
[New Thread 0x2603 of process 5623]
[New Thread 0x2303 of process 5623]
hello, world: 9, 36
[Inferior 1 (process 5623) exited normally]
(gdb)
```

Oddly, pushing `gdb` to continue causes it to function as normal.
Unfortunately, when running in batch mode (as `cygdb` does on loading), those
questions will automatically be answered `y`, which currently makes `cygdb`
unusable.

A couple of points about this error:

 1. it appears only when using `file` to load debugging symbols; doing
    `add-inferior -exec main` will work fine.
 2. despite claiming that `pid` is 0 in `find_inferior_pid`, `gdb` seems to
    have successfully found it by the time it runs the inferior.
 3. regular initialisation and `add-inferior` do not cause `gdb` to call
    `find_inferior_pid`, and their temperatmental hangs may suggest that there
    is a deeper underlying problem that is only noticed occasionally.

Right now I have to start work on other parts of QuTiP, but I will hopefully
return to solve the last problem!


[cython]: https://cython.org/
[gdb]: https://www.gnu.org/software/gdb/
[homebrew]: https://brew.sh/
[gnu-codesign]: https://gcc.gnu.org/onlinedocs/gnat_ugn/Codesigning-the-Debugger.html
