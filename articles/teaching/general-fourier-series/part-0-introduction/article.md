In all my time as a PhD student I have been involved with teaching undergraduate
and postgraduate physics students at Imperial College London (they even [gave me
a prize][fons-prize] in 2018!) as a teaching assistant in classroom-style
tutorials and seminars.  For my final year, though, I've also moved up into
helping write the teaching materials, particularly for the differential
equations part of the second-year course.

The first differential equations seminar we had was showing off some of the
properties and uses of the [Legendre polynomials][legendre], which the students
had just met by solving Legendre's equation.  My part of the seminar was
illustrating how any orthogonal basis of functions can be used to make a series
expansion, and then getting the students to investigate how different types of
functional expansion behave at different orders.  If you just want to play with
this, load up the Jupyter notebook on [Colab][colab] or [myBinder][mybinder].
The [source code for this notebook][source] is available on GitHub.  You can see
an example plot of these below.

<img src="${article_a02a84}polynomial-high.svg" alt="Series approximations of a
twelfth-order polynomial using many terms in the expansion.">

The end result we'll achieve mathematically is an abstract way of making series
expansions.  In general, a series expansion approximates a function $`f(x)`$
by using a (possibly infinite) sequence of terms, where each term is a constant
multiplied by some basis function.  Different series expansions use different
bases and different methods of determining the coefficients.

Perhaps the most familiar example is the Taylor series.  The Taylor series
$`T_f(x)`$ that approximates a function $`f(x)`$ around some point $`x_0`$ is

\[
    T_f(x) = \sum_{k=0}^\infty \frac{f^{(k)}(x_0)}{k!}{(x-x_0)}^k,
\]

where the $`f^{(k)}(x_0)`$ notation means the $`k`$th derivative of $`f(x)`$
with respect to $`x`$, evaluated at $`x_0`$.  This series uses the monomials
($`x^m`$ for integer $`m`$) as its basis, and it's very common in physics to use
finite approximations to the Taylor series (_i.e._ by taking only the first
$`m`$ terms) to analyse behaviour of a complicated function around some point.

Taylor series are taught at A Level in the UK, and are the first functional
approximation method most people come across.  Early in undergraduate physics
courses, we introduce another method, motivated by investigation of periodic
functions: the Fourier series.  For real-valued functions where the range
$`-1 \le x < 1`$ spans one period, this is generally written as

\[
    F_f(x) = \frac12 a_0 + \sum_{k=1}^\infty \Bigl( a_k\cos(k\pi x) + b_k\sin(k\pi x) \Bigr),
\]

where $`a_k = \int_{-1}^1 f(x)\cos(k\pi x)\mathrm{d}x`$, and the $`b_k`$ are the
same except for $`\sin`$ instead of $`\cos`$.  The basis functions of this
series are $`\sin(m\pi x)`$ and $`\cos(m\pi x)`$ for integer $`m`$.

Fourier series are constructed by using an idea of "orthogonality" of its basis
functions, whereas Taylor series come from locally approximating a function with
successive polynomials.  We haven't yet seen _why_ the Fourier coefficients are
the way they are, but once we have, we can use the same method to make many
different series expansions.  First, though, we take an apparent detour into
linear algebra and vectors---if you already know what an "inner-product space"
is, there's probably nothing new for you in the next part.

The [next article of this series][part1] runs through the all the background
maths for this part of the seminar, including some linear algebra results that
the students learned in their first year at university.  The rest of the series
covers how to produce the arbitrary series expansions, then looks at the
results I hoped the students would discover by playing around with the
interactive notebook.

[fons-prize]: https://www.imperial.ac.uk/natural-sciences/education-and-teaching/fons-annual-prizes-for-excellence/
[legendre]: https://en.wikipedia.org/wiki/Legendre_polynomials
[colab]: https://colab.research.google.com/github/jakelishman/2020-imperial-yr2-differential-equations/blob/main/Series_Expansion_Approximations.ipynb
[mybinder]: https://mybinder.org/v2/gh/jakelishman/2020-imperial-yr2-differential-equations/main?filepath=Series_Expansion_Approximations.ipynb
[source]: https://github.com/jakelishman/2020-imperial-yr2-differential-equations/

---

This article is the introduction to a series.  You can find all of the rest of
the articles in this series here:

- [Part 0: Introduction to Series Expansions][part0]
- [Part 1: Linear Algebra Basics][part1]
- [Part 2: Making Series Expansions From Orthogonal Polynomials][part2]
- [Part 3: Comparing Different Series Expansions][part3]

[part0]: ${article_404ffd}
[part1]: ${article_080743}
[part2]: ${article_ce0047}
[part3]: ${article_a02a84}
