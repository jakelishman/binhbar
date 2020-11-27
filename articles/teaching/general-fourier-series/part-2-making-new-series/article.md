In [the first part of this series on series expansions][part1]
([introduction][part0]), we defined several concepts from first-year linear
algebra that we need to work in a general, abstract setting rather than having
to repeat the same derivations over and over again.  We are now looking at the
topic at the centre of this series; generalising the Fourier series method.

Amazingly, the few definitions I gave in the previous article let us define a
whole family of different functional series expansions.  Like before, we will
consider only continuous, finite functions defined on the interval $`[-1, 1]`$.
Let's say we have a basis of functions that are orthogonal under the inner
product

\[
    \langle f,g\rangle = \int_{-1}^1 f(x) g(x)\,\mathrm dx.
\]

One example of this is the trigonometric functions $`\sin(k\pi x)`$ and
$`\cos(k \pi x)`$ for all non-negative integers $`k`$.  It's beyond the scope
of undergraduate physics courses to [prove that the trigonometric functions
span this space][trig-complete], but they do, and you also can verify that the
inner-product integral is indeed zero for any unequal pair.  We'll refer to
elements of this basis as $`\phi_n(x)`$, where $`n`$ is just a unique label.

Now, since the functions span the space of functions we can write down any
function $`f`$ in terms of our basis $`\phi_n`$ and some scalar coefficients
$`c_n`$ as

\[
    f(x) = \sum_{n=0}^\infty c_n \phi_n(x),
\]

and this series is unique.  For convenience, we'll call the series
representation $`F_f`$ to distinguish it from $`f`$ while we're still
determining the coefficients.

This isn't very helpful without knowing what the $`c_n`$ _are_, but since our
$`t_n`$ form an orthogonal basis, we can use some properties of the inner
product to find them.

First we need a measure of how good our choice of $`c_n`$ are.  For this we use
the idea of magnitude: define the "error" vector (function) $`r`$ as

\[\begin{aligned}
    r(x) &= f(x) - F_f(x) \\
         &= f(x) - \sum_{n=0}^\infty c_n \phi_n(x),
\end{aligned}\]

and now we want to minimise the magnitude squared $`\langle r,r \rangle`$.
Using the properties of the inner product, we find

\[\begin{alignedat}2
    \langle r, r\rangle &= \langle f-F_f, f-F_f \rangle && \\
    &= \langle f,f\rangle - 2\langle f,F_f\rangle + \langle F_f,F_f\rangle &&\text{(by linearity and symmetry)}\\
    &= \langle f,f\rangle - 2\sum_{n=0}^\infty c_n \langle f, \phi_n\rangle
        + \sum_{n=0}^\infty\sum_{m=0}^\infty c_n c_m \langle \phi_n,\phi_m\rangle &&\text{(by linearity)}\\
    &= \langle f,f\rangle - 2\sum_{n=0}^\infty c_n\langle f,\phi_n\rangle +
    \sum_{n_0}^\infty c_n^2 \langle \phi_n,\phi_n\rangle &&\text{(by orthogonality).}
\end{alignedat}\]

The last line follows because orthogonality of the functions implies

\[
    \langle \phi_n, \phi_m \rangle = \begin{cases}
        \langle \phi_n, \phi_n \rangle &\text{if $n = m$} \\
        0 &\text{if $n \ne m$.}
    \end{cases}
\]

Now we try to minimise $`\langle r,r\rangle`$ with respect to each of the
$`c_n`$ by setting the derivatives to zero:

\[\begin{aligned}
    0 &= \frac\partial{\partial c_n}\langle r,r \rangle \\
    &= 2c_n\langle\phi_n,\phi_n\rangle - 2\langle f,\phi_n\rangle,
\end{aligned}\]

so we find that

\[
    c_n = \frac{\langle f,\phi_n\rangle}{\langle\phi_n,\phi_n\rangle}.
\]

We should make sure that this is a _minimum_, not a maximum.  This is quite
simple---since there's only one value, we know that this is the only extreme
point and that if we added on some really large number to all the $`c_n`$ then
the approximation would obviously be worse.  This makes the single extremum a
minimum for certain.  We could also do the more rigorous [second-derivative
test][derivative-test], which would also show us that it is a minimum as
$`\langle \phi_n,\phi_n\rangle > 0`$ is a property of the inner product.

This solution for $`c_n`$ is really a remarkable result.  You can put in the
trigonometric definitions of the $`\phi_n`$ and see that it retrieves the
definitions of the Fourier series coefficients way up at the top of this
article.

What's more impressive, however, is that everything we did _did not care what
the $`\phi_n`$ were_!  In fact, they only had to be an orthogonal basis; the
trigonometric functions were just one possibility.

Another valid basis we could have used is made up of polynomials; the monomials
$`x^n`$ themselves aren't orthogonal under this inner product, but there is a
method called the [Gram--Schmidt procedure][gram-schmidt] that can be used to
turn them into an orthogonal basis.  If you do this, you come up with a series
of polynomials $`P_n(x)`$ called the [Legendre polynomials][legendre].  The
first few of these are

\[\begin{aligned}
    P_0(x) &= 1,\\
    P_1(x) &= x,\\
    P_2(x) &= \frac12(3x^2 -1),\\
    P_3(x) &= \frac12(5x^3 - 3x).\\
\end{aligned}\]

These appear in the expansion of the [electrostatic potential around a
multipole][multipole] in Cartesian coordinates, and consequently in the
[spherical harmonic functions][spherical-harmonics], which turn up all over
physics.

Now this basis is also orthogonal, so if we want to make a "Fourier--Legendre"
series expansion of $`f`$ called $`L_f`$

\[
    L_f(x) = \sum_{n=0}^\infty \ell_n P_n(x),
\]

then we already know that the coefficients $`\ell_n`$ are defined by

\[
    \ell_n = \frac{\langle f,P_n\rangle}{\langle P_n,P_n\rangle}.
\]

_This_ is why abstract concepts in linear algebra are so useful; with no
additional work we gained a whole new method of series expansion!

In [the next part of this series][part3], we'll compare how this new Legendre
series expansion behaves in comparison to the Fourier and Taylor series.

[legendre]: https://en.wikipedia.org/wiki/Legendre_polynomials
[trig-complete]: https://math.stackexchange.com/a/317004/206819
[derivative-test]: https://mathworld.wolfram.com/SecondDerivativeTest.html
[gram-schmidt]: https://en.wikipedia.org/wiki/Gram%E2%80%93Schmidt_process
[multipole]: https://en.wikipedia.org/wiki/Multipole_expansion#Multipole_expansion_of_a_potential_outside_an_electrostatic_charge_distribution
[spherical-harmonics]: https://en.wikipedia.org/wiki/Spherical_harmonics

---

This article is the second part of a series.  You can find all of the rest of
the articles in this series here:

- [Part 0: Introduction to Series Expansions][part0]
- [Part 1: Linear Algebra Basics][part1]
- [Part 2: Making Series Expansions From Orthogonal Polynomials][part2]
- [Part 3: Comparing Different Series Expansions][part3]

[part0]: ${article_404ffd}
[part1]: ${article_080743}
[part2]: ${article_ce0047}
[part3]: ${article_a02a84}
