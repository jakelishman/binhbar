Overhauling the internals of a mathematical library is no good if no other
developers on the team know how to use the new systems you've put in place, and
don't know why you've made the choices you've made.  In the last week I've been
writing a new QuTiP developers' guide to the new data layer that I'm creating
as part of my Google Summer of Code project, which has involved learning a lot
more about the [Sphinx][sphinx] documentation tool, and a little bit of GitHub
esoterica.

Currently we don't have a completely plan for how this guide will be merged
into the QuTiP documentation, and where exactly it will go, so for now it is
hosted on [my own GitHub repository][my-devguide-repo].  I have also put up a
properly rendered version on [a GitHub pages site linked to the
repository][gh-pages-devguide].

My Sphinx [`conf.py`][conf.py] file for this repository is not (at the time of
commit [0edf49e][0edf49e]) very exciting.  Fortunately, Sphinx largely just
works out-of-the-box as one would expect from a mature Python project.  Perhaps
the boldest part of that file is the `intersphinx_mapping` dictionary, which
uses the `intersphinx` built-in to link to other projects' documentation also
built with Sphinx.

Right now, the `intersphinx` documentation is perhaps a little lacking, and
sometimes seems to just involve some hope (and some disappointment).  In
particular, I have several external references set up as

```python
intersphinx_mapping = {
    'qutip': ('http://qutip.org/docs/latest/', None),
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference/', None),
    'cython': ('https://cython.readthedocs.io/en/latest/', None),
}
```

but so far I have not been able to find how to associate a reference symbol
like ``:c:func:`PyDataMem_NEW` `` with the `numpy` namespace specifically.
In the Python role this is generally not much of a problem, as objects tend to
come with Python namespaces attached like ``:py:class:`numpy.ndarray` ``, but
in C APIs like `PyDataMem_NEW`, we seem to just have to hope that there aren't
any naming collisions.

Another nuisance is the difficulty of working out which symbols should be
referenced with which roles.  I have found two ways for extracting data about
the contents of an object inventory.  The first is the "first-class" method,
simply by calling the `intersphinx` module as a Python executable, such as
(output shortened)

```
$ python -msphinx.ext.intersphinx https://numpy.org/doc/stable/objects.inv
c:function
	NPY_AUXDATA_CLONE    reference/c-api/array.html#c.NPY_AUXDATA_CLONE
	NPY_AUXDATA_FREE     reference/c-api/array.html#c.NPY_AUXDATA_FREE
c:var
	NPY_ARRAY_OWNDATA    reference/c-api/array.html#c.NPY_ARRAY_OWNDATA
py:class
	numpy.ndarray        reference/generated/numpy.ndarray.html#numpy.ndarray
```

This works quickly and can be `grep`-ed through, but it's a little inconvenient
as often the role (e.g. `py:class` or `c:function`) is far away from the item
you want to view.  A second possibility is the tool [`sphobjinv`][sphobjinv],
which can be installed via `pip`.  This can use fuzzy matches to search the
object database using `sphobjinv suggest` or simply dump everything out into a
nicer form with `sphobjinv convert`.  If you are going to use the suggestion
feature, it's best to install `python-levenshtein` from either `pip` or
`conda`, as this implements a _much_ faster matcher.

One problem that I have found is that the Sphinx roles do not always line up
with what we expect, even accounting for these two tools outputting the "block
directives", and cross-references needing the "inline directive" form.
Currently, the NumPy C flag `NPY_ARRAY_OWNDATA` is reported to be of type
`c:var` by Sphinx and `sphobjinv`, but attempting to reference
``:c:var:`NPY_ARRAY_OWNDATA` `` fails.  I found (by coincidental reference in
the NumPy commit history) that the reference should instead be
``:c:data:`NPY_ARRAY_OWNDATA` ``, despite
[the Sphinx website assuring me][sphinx-c-role] (dated: 2020-06-29)

> `c:member`, `c:data`, and `c:var` are equivalent.

Despite all this, the Sphinx build process has gone smoothly for me, and
running `make html` is fast and easy.  I have found that Sphinx likes to serve
its static content from a folder called `_static`, which is somewhat a problem
when using GitHub pages, which by default ignores all directory entries which
start with an underscore.  Fortunately there is a fix for this, but it is not
really documented other than by users' complaints in GitHub issue trackers that
things are broken.

The solution is just to drop an empty file called `.nojekyll` into the root
directory that the GitHub pages site is hosted in.  This works because GitHub
uses [Jekyll][jekyll] to convert Markdown and Liquid template files into
regular pages, and the special `.nojekyll` file disables all this processing.
We don't need it anyway, because Sphinx has already done it for us, and much
more besides.


[sphinx]: https://www.sphinx-doc.org/en/master/
[my-devguide-repo]: https://github.com/jakelishman/qutip-devguide/
[gh-pages-devguide]: https://jakelishman.github.io/qutip-devguide/
[0edf49e]: https://github.com/jakelishman/qutip-devguide/tree/0edf49e
[conf.py]: https://github.com/jakelishman/qutip-devguide/blob/master/conf.py
[sphobjinv]: https://github.com/bskinn/sphobjinv
[sphinx-c-role]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#cross-referencing-c-constructs
[jekyll]: https://jekyllrb.com/
