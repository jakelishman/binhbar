For this summer, I will be working full-time on the open-source project
[QuTiP][qutip] with a stipend provided by Google as part of the [Summer of Code
2020][gsoc] project to the umbrella organisation [numFOCUS][numfocus].  One
requirement of the stipend is that I blog about what I am working on throughout
the project, and on any interesting parts of team programming I encounter, so
that future applicants to the programme have an idea of what to expect.  I will
be doing that here, under the "[GSoC](/tags/gsoc/)" tag.

QuTiP is a Python library for dynamics simulations of open quantum systems,
something that I have made heavy use of during my PhD studies.  At its core is
the `Qobj` class, which represents all quantum objects.  Currently, the
underlying data storage format is always a compressed-sparse-row matrix,
which allows efficient simulation of very large tensor-product spaces, but
introduces significant overhead when handling smaller, few-qubit systems.  The
aim of the project is to abstract out the data layer so that higher-level
components can function seamlessly without worrying about the representation
format, but the advanced user will be able to access accelerated functions by
using the right tool for the job.  You can also read my [full project
proposal][proposal] in PDF format hosted here.

[qutip]: http://www.qutip.org
[gsoc]: https://summerofcode.withgoogle.com
[numfocus]: https://numfocus.org
[proposal]: ${article_root}/proposal.pdf
