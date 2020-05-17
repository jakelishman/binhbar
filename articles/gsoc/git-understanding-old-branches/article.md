I will be refactoring and reorganising [QuTiP's][qutip] internal data
structures, a large task that was previously attempted by someone else but one
that never quite got completed and lives in a disused branch on their fork.  In
the intervening year or so, the codebase has moved on significantly, so GitHub
now sounds the death knell

> This branch is 85 commits ahead, 366 commits behind qutip:master. 

I want to know what changes they had made, without being inundated by unrelated
changes on the `master` branch.

Let's assume that the old branch of interest is called `old-feature` and lives
in a forked repository which I have added as a remote called `fork`.


## Getting the diff

The tool for showing changes is, predictably, `git diff`.  I cannot just do a
standard call to
```bash
git diff qutip/master fork/old-feature
```
because I end up with `201 files changed, 14255 insertions, 17882 deletions`,
since I also see all the changes that `master` made as well.  Instead, I want to
see all the changes that happened on `fork/old-feature` since it diverged.  I
can find the hash of this commit by using `git merge-base` with
```bash
git merge-base qutip/master fork/old-feature
```
so I can combine these two to get a more useful diff with
```bash
git diff $(git merge-base qutip/master fork/old-feature) fork/old-feature
```
In fact, this is such a useful feature that there is even a short-hand for it:
diff's triple-dot notation
```bash
git diff qutip/master...fork/old-feature
```


## Searching the commit history

Using `git diff` I can see the total of all the changes to the code, but there
may also be some useful information stored in the commit messages.  These are
accessed, as always, through `git log`.

A quick glance at the manpages (sidenote: `git` subcommands' manpages are
accessed by hyphenated the command together, such as `man git-log`) tells us
that `git log` understands a similar-looking two-dot (`..`) and three-dot
(`...`) syntax to what we just used in `git diff`.  Here we must be very
careful; `git diff` and `git log` treat the dots almost completely conversely to
each other.

The three-dot form here is called the "symmetric difference" of two references.
The set `branch-a...branch-b` now means all the commits that are ancestors of
`branch-a` _or_ `branch-b`, but not both.  This means that we will get all the
commits which happened on either branch since the two were split from each
other.  In other words, this is what `git diff` was doing _before_ we put in the
triple dots!

Instead, we want the two-dot form, as in `branch-a..branch-b`.  This form is the
"range" notation, and means all commits which are ancestors of `branch-b` but
not of `branch-a`.  This way we only see the changes on `branch-b` since it was
split off, even if `branch-a` also changed.

Our command to see the commits made only on the old branch, then, is
```bash
git log qutip/master..fork/old-feature
```
As always, I can use the `pathspec` arguments to `git log` to limit the commits
to only the files I ask for, so if I only want to look at changes to the tests,
I can run
```bash
git log qutip/master..fork/old-feature -- qutip/tests
```
Here the `--` is a command-line switch which `git` (and many Unix utilities) use
to separate out options from files.  This is clearly useful in this case,
because the directory `qutip/tests` looks a lot like the branch `qutip/master`!

Now that I've seen the code changes and some explanation of the thought process
and history behind those changes as they were being made, hopefully I'll not
need to reinvent the wheel so much when trying to implement it myself!

[qutip]: http://qutip.org
