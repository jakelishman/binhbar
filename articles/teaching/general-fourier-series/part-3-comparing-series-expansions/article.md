In [the second part of this series on series expansions][part2]
([introduction][part0]), we found a way to make a series expansion using any
basis of orthogonal polynomials.  This is how the standard Fourier series is
defined, and then we also used it to make a series expansion out of the
[Legendre polynomials][legendre].  Now we're going to compare how these behave
with different numbers of terms.

This is finally the fun part of the seminar!  My second-year physics students
should generally have already known the previous two articles from first-year
courses, so they started here, pretty much.  To interact with these series
expansions, you should load up my Jupyter notebook on either [Colab][colab] or
[myBinder][mybinder], and try plotting your own functions and seeing how the
expansions behave.

In reality we don't use the infinite form of series expansions, we only use the
first few terms to get a good approximation of a function.  The notebook is used
for investigating how different series expansions work with comparably few
terms, and which would be most appropriate in a given situation.  The series
there are the standard Fourier series, the Fourier--Legendre series, and the
Taylor series about $`x=0`$ (which is formed by a different method to the other
two).  If you need a reminder of how these series look like, the Taylor and
Fourier series forms were given [in the introduction][part0], and the
Legendre series was derived [in part two][part2].

I asked the students to consider a couple of the following questions, and
discuss them in groups of around five:

- Which series would you call the "most accurate"?  Why?  Does it depend on the
  function?
- What sorts of functions are the different expansions best at approximating?
  Which are they bad at?
- The Legendre series often seems to "give up" in the middle of some shapes at
  low orders (_e.g._ sinusoids).  Why is this, and are there any things the
  series is still useful for?
- The Taylor series almost invariably has the largest pointwise error.  Why is
  this?  What is the Taylor series useful for?

Let's look at some examples to illustrate what I hoped the students would
discover, and then afterwards I'll explain why all of these effects appear.


## Approximating a polynomial

How do the series behave if we attempt to approximate a polynomial function?
I'm using a twelfth-degree polynomial, so

\[
    f(x) = c_0 + c_1 x + c_2 x^2 + \dotsb + c_{12} x^{12},
\]

for some arbitrary coefficients that I picked to give a nice shape.  Below I've
plotted this function in the range $`x \in [-1,1]`$ (in dashed black), and the
Taylor, Legendre and Fourier series approximations with 13 terms each.

<img src="${article}polynomial-high.svg" alt="Series approximations to a high-order polynomial using 13 terms.">

Since it's a polynomial, given enough terms the Taylor series and Legendre
series become exact.  The Fourier series is not based on polynomials, though,
so that remains an approximation even with this many terms.

What's more interesting is how the series behave when there are only very few
terms.  This second graph is the exact same approximations, but with only the
first five terms of each expansion.

<img src="${article}polynomial-low.svg" alt="Series approximations to a high-order polynomial using 5 terms.">

Here we are starting to see what the series really care about.  The Taylor
series is a very poor approximation far from its central point of $`x=0`$, but
it is the only expansions which even seems to get _any_ of the behaviour
correct.  The Fourier and Legendre series are approximately right _on average_
across the whole function, but at any given point, they don't really look like
it at all.


## Approximating a Lorentzian function

Let's move away from "nice" polynomials.  This next function is a
[Lorentzian][lorentzian] if you're a physicist, or a scaled Cauchy distribution
if you're into statistics.  As a probability distribution this has the form

\[
f(x) = \frac1{\pi\varGamma\Bigl[1 + {\bigl(\frac{x-x_0}{\varGamma}\bigr)}^2\Bigr]},
\]

for some width parameter $`\varGamma`$.

As a probability distribution, this can actually be a really tricky function to
work with---we call it "pathological" because while it's clearly symmetrical and
has an obvious mean, the proper mathematical definition

\[
\langle x\rangle = \int_{-\infty}^\infty x f(x)\,\mathrm dx
\]

doesn't exist!  The integral doesn't converge, nor do higher-order statistical
moments like the variance.  It's still a function, though, and we can
approximate it with our expansions.

<img src="${article}lorentzian-low.svg" alt="Series approximations to a Lorentzian function using 5 terms.">

At low orders, we see the same behaviour of the Taylor series; it is the only
approximation that even seems to make any effort to be close near the top of the
peak, but then the polynomial approximation completely gives up.  The Legendre
and Fourier expansions here look fairly similar.

<img src="${article}lorentzian-high.svg" alt="Series approximations to a Lorentzian function using 13 terms.">

Adding many terms here doesn't really change the Taylor series much, but the
Fourier and Legendre series become significantly better.  These approximations
notionally have 13 terms in them, just like for the polynomial above, but really
we can see from the function and the basis vectors that this won't truly be the
case; the function is clearly perfectly even, so no odd functions in the bases
will contribute.  In effect, this means that the Lorentzian is only being
approximated by three and seven terms, though even if you use [the attached
notebook][colab] to add many more terms yourself, you'll struggle to get the
Taylor series to look good.

Functions that are asymptotically flat are generally a problem for polynomial
expansions; an $`n`$th-degree polynomial naturally goes as $`x^n`$ for large
$`n`$.  When only considering a small domain, as we are here, expansions can
give quite a lot of insight.


## Approximating a logistic function

Finally, before we look at why these particular series expansions have these
traits, let's approximate the machine-learning enthusiast's favourite type of
the function: the logistic map.  This particular one is

\[
f(x) = \frac1{1 + e^{-5x}},
\]

and you can see its characteristic sigmoid ("s") shape.  Again, this tends to
become flat, so we expect the Taylor series to struggle to find any convergence
at the edges.

<img src="${article}logistic-low.svg" alt="Series approximations to a logistic function using 5 terms.">

On the face of it, the logistic function is neither even nor odd, since it
doesn't pass through zero.  However, given a single constant offset of one half,
which is the lowest-order term in all of these expansions, it is actually odd.
Similarly to the Lorentzian, then, only half of the subsequent terms will
actually contribute to the approximations.

<img src="${article}logistic-high.svg" alt="Series approximations to a logistic function using 13 terms.">

The most striking feature in this high-order approximation plot, perhaps, is the
divergence of the Fourier series from the Legendre one at the edges, and the
wiggles the Fourier approximation has towards these edges.  Previously these two
have generally been rather similar.  The Legendre series is much better at
approximating the logistic map than the Lorentzian, likely due to much smaller
magnitude second derivatives of the function.


## Understanding what we've seen

So far we haven't attempted to explain _why_ we have seen things, we've only
commented on _what_ is present.  Let's go through and explain the parts now.

_The Taylor series is only good close to $`x=0`$._  This is straightforward; the
Taylor series is defined by successively making a better approximation around a
given point.  The series is extended by adding information from higher and
higher order derivatives, and uses no knowledge of far-away points.

_The Fourier and Legendre series are good on average._  This is again because of
how the series are defined.  In [the previous part][part2], we saw that we found
the series coefficients by minimising $`\langle r,r\rangle`$, where $`r(x) =
f(x) - A_f(x)`$ was a "residual" or "error" function describing the difference
between the true function $`f`$ and the approximation $`A_f`$.  Since these
inner products are integral, this is a minimisation of the [root-mean-square
error][rms] over the domain.  In simpler words, these series expansions are
designed to be good when averaged over every point in the interval we are
considering, and the integral forms of their coefficients ensure that the
expansions make use of data from everywhere relevant to achieve this.  This
property makes these series, and particularly the Legendre series, excellent for
producing [numerical integration][gaussian-quadrature] rules of very high
orders.

_The Taylor and Legendre series were perfect when given a polynomial._  Since
they use polynomials as their basis functions, these series will naturally
become perfect once they have enough terms.  It's easy enough to see that there
_is_ a possible solution using Legendre polynomials up to and including the
degree of the polynomial; choose the coefficient of highest-degree Legendre
polynomial to match the highest-degree term in the function, then do the same
for the next-highest-degree terms taking into account what's already present in
the expansion, and so on.  This gives a perfect result with no higher-order
terms, and consequently also has zero error, since it's the same function.  Now
we can also know that our method must reproduce this solution we've shown
exists, because the minimum possible root-mean-square error of _any_ function is
zero, and our coefficients by definition minimise the root-mean-square error.
The Fourier series does not use polynomials, and so never becomes exact for
such functions; you must sum an infinite number of cosine waves of differing
frequencies to approximate an $`x^2`$ term.

_The Fourier series deviates when the function values on the left- and
right-hand sides of the domain are not equal._  This is actually one of the nice
properties of Fourier series, though it doesn't look like it here.  As the
Fourier series is based on the periodic trigonometric functions, the Fourier
approximations are always also periodic, and the large divergence at the very
end is the approximation keeping itself continuous between periods.  I've only
plotted the approximations between $`-1`$ and $`1`$, but if we extended it
beyond that, we'd see the Fourier series repeat again and again, while the
Legendre expansions would shoot off to infinity in a similar manner to the
Taylor series.  Of course for our purposes, this is totally fine; these
approximations were only _meant_ to work within this region, and [extrapolation
is usually a sin in physics][extrapolation].

_The Fourier series has large oscillations near a jump._ This "ringing" effect
of the Fourier series is called the [Gibbs phenomenon][gibbs], and it's a rather
funny behaviour that often appears near discontinuities.  As the number of terms
goes to infinity, the [Fourier series will converge][riesz-fischer] for every
point of a [square-integrable function][l2] (most sensible functions---very
roughly these are functions that aren't fractals and don't have an infinite
asymptote inside the boundaries).  However, the maximum point-wise absolute
divergence actually increases as you add more terms; the "ears" get thinner and
closer to the jump, but they also get taller and taller.  Each point converges
individually, but in every Fourier approximation the worst point (which moves
over time) gets worse and worse.  This happens because the series must remain
_analytic_---all its derivatives exist---everywhere, but it also needs to
approximate an infinite gradient.  The only way to do that is by these wiggles.


## Wrapping up

This series of posts has covered the maths behind making new series expansions
using a generalised version of the Fourier-series method, based on a seminar I
wrote for the whole second-year physics undergraduate cohort at Imperial College
London.  These series have many interesting properties, depending on which basis
set of orthogonal polynomials are used.  If you didn't take the time at the
start to do so, please do have a play with my example Jupyter notebook on
[Colab][colab] or [myBinder][mybinder] to see how these series work with
different functions!


[legendre]: https://en.wikipedia.org/wiki/Legendre_polynomials
[lorentzian]: https://en.wikipedia.org/wiki/Cauchy_distribution
[colab]: https://colab.research.google.com/github/jakelishman/2020-imperial-yr2-differential-equations/blob/main/Series_Expansion_Approximations.ipynb
[mybinder]: https://mybinder.org/v2/gh/jakelishman/2020-imperial-yr2-differential-equations/main?filepath=Series_Expansion_Approximations.ipynb
[rms]: https://en.wikipedia.org/wiki/Root-mean-square_deviation
[extrapolation]: https://xkcd.com/605/
[gibbs]: https://en.wikipedia.org/wiki/Gibbs_phenomenon
[riesz-fischer]: https://en.wikipedia.org/wiki/Riesz%E2%80%93Fischer_theorem
[l2]: https://en.wikipedia.org/wiki/Square-integrable_function
[gaussian-quadrature]: https://mathworld.wolfram.com/GaussianQuadrature.html

---

This article is the last part of a series.  You can find all of the rest of
the articles in this series here:

- [Part 0: Introduction to Series Expansions][part0]
- [Part 1: Linear Algebra Basics][part1]
- [Part 2: Making Series Expansions From Orthogonal Polynomials][part2]
- [Part 3: Comparing Different Series Expansions][part3]

[part0]: ${article_404ffd}
[part1]: ${article_080743}
[part2]: ${article_ce0047}
[part3]: ${article_a02a84}
