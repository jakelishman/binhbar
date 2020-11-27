In [the introduction to this series of articles][part0], we introduced the idea
of a series expansion, and saw the explicit forms of the Taylor and Fourier
series.  We are building towards a generalised series expansions based on
"orthogonal" polynomials, but first we have to define some concepts from linear
algebra.  This article is roughly at the level of early first-year physics
undergradutes.

Students at this level have come across the word "orthogonal" before when
talking about Euclidean ("normal") vectors.  Here it means the same thing as
"perpendicular" or "at right angles", at least while you have three or fewer
dimensions.  Once you have more than that, or you're dealing with some other
type of vector, the definition is a little more abstract.


## What is a vector?

What other types of vector are there?  In pre-university physics, we usually
describe a vector as a quantity which has both a magnitude and a direction.
This is a Euclidean vector.  Mathematically, though, the definition of a vector
is more general than this; a vector is an element of a set of objects that have
some defined operations between them (a "vector space").  There's also a
requirement that the vectors are "over a scalar field $`\mathcal F`$", but for
our purposes we will always just be using real numbers for this.

To be a valid set of vectors $`\mathcal V`$ over the real numbers, we just need
to have two defined operations: an abstract "addition" and "scalar
multiplication".

Addition can be any operation that satisfies the rules

- $`\bm x + (\bm y + \bm z) = (\bm x + \bm y) + \bm z`$,
- $`\bm x + \bm y = \bm y + \bm x`$,

for all vectors $`\bm x`$, $`\bm y`$ and $`\bm z`$ in $`\mathcal V`$, and the
set of elements needs to contain a special vector $`\bm 0`$ that doesn't do
anything when added to any other vector.  The collection of vectors also needs
to contain an "inverse" vector for every member under addition, so that for
every vector $`\bm x`$ in $`\mathcal V`$ there is another vector $`\bm y`$ that
satisfies $`\bm x + \bm y = \bm 0`$.  You can see that the way you were
taught to add Euclidean vectors together trivially satisfies all these rules.

The scalar multiplication operation has to satisfy some more rules in
conjunction with the vector addition ones:

- associativity: $`\alpha (\beta\bm x) = (\alpha\beta) \bm x`$,
- multiplicative identity: $`1\bm x = \bm x`$,
- vector addition distributivity: $`\alpha (\bm x + \bm y) = \alpha\bm x + \alpha \bm y`$,
- scalar addition distributivity: $`(\alpha + \beta)\bm x = \alpha\bm x + \beta\bm x`$,

for all scalars $`\alpha`$ and $`\beta`$ and vectors $`\bm x`$ and $`\bm y`$.
Again, this is familiar with Euclidean vectors.

Now, since these rules are quite abstract, there are lots of things that can
_also_ be valid vector spaces.  These are separate to Euclidean vectors; you
can't add vectors from different spaces together.  Here, we're most interested
in looking at functions defined in certain intervals (different intervals would
be different vector spaces).  It's also interesting to note that even scalar
numbers satisfy this definition of a vector space!

The notions of addition and scalar multiplication apply fairly straightforwardly
to functions which return real numbers.  If I have a function $`f`$, then $`2f`$
is the function that does the same thing as $`f`$, then multiplies the result by
two.  Similarly, the result of $`f + g`$ is a function which adds together the
outputs of $`f`$ and $`g`$.  You can check that all the other rules are
satisfied too; perhaps the least obvious one is the existence of the "zero"
vector.  In this case, that's just a function that takes any input and returns
the scalar zero.

The reason we do things like this mathematically is to apply one result to many
different systems.  There are lots of results that can be proved simply from the
abstract rules I presented above.  Now if you can show that a new system you've
just come up with satisfies these rules, you get a whole lot of results for
free.


## Inner products and orthogonality

So far we haven't said anything about orthogonality.  That's actually because
the base definition of a mathematical vector doesn't include it; your vector
space needs to have some extra structure in the form of a new operation for it
to be defined.  Think about how you check if two Euclidean vectors are
perpendicular---you see if the "dot product" is zero.  The dot product is an
example of this new operation, which in its abstract form we call an "[inner
product][inner-product]".  It takes two vectors as arguments and returns a
scalar.

When we call it an inner product we denote the operation as
$`\langle \bm x, \bm y\rangle`$.  This might be unfamiliar, since the dot
product is usually denoted with (unsurprisingly) a dot.

Just like before, the inner product has a few rules that go along with it.
These are rather more complicated, but that's to be expected from an operation
that provides us with so much more structure in our space.  The rules when the
scalars are the real numbers are

- linearity in the first argument:
  $`\langle \alpha\bm x + \beta\bm y, \bm z\rangle
  = \alpha\langle\bm x,\bm z\rangle + \beta\langle\bm y,\bm z\rangle`$,
- symmetry: $`\langle \bm x, \bm y\rangle = \langle \bm y, \bm x\rangle`$,
- positive-semidefiniteness: $`\langle\bm x, \bm x\rangle \ge 0`$ with
  equality if _and only if_ $`\bm x = \bm0`$.

These lead to some really interesting abstract interpretations.  The last point
leads straight into the idea of "length", or lets us define a distance between
two vectors.  Technically this is called a "norm", though we won't worry about
all the additional rules that go along with that.  You can see by comparison to
Euclidean vectors that $`\sqrt{\langle \bm x, \bm x\rangle}`$ produces a
quantity that we could call the "magnitude" of a vector; it's always a positive
number, and it's zero only if the vector is the zero vector we defined earlier.

It also leads to the idea of measuring "how similar" two vectors are.  You might
have called this "the projection of one vector along another" when you learned
about Euclidean vectors.  [You can show that][cauchy-schwarz]

\[
    {\langle \bm x, \bm y\rangle}^2
    \le \langle\bm x,\bm x\rangle \langle\bm y,\bm y\rangle
\]

for all vectors $`\bm x`$ and $`\bm y`$ in any vector space that satisfy the
rules we set out above, where the equality happens only if
$`\bm x = \alpha\bm y`$.  This last relation is the generalised form of two
vectors being "parallel".  Another way of looking at this is to define "being
parallel" as two vectors being equal when you divide them by their magnitudes.
Scalar division by $`\alpha`$ is technically not defined yet, but
we can rephrase it as scalar multiplication by $`1/\alpha`$.  The two vectors
are "more similar" when they are close to parallel, in the sense that the
inequality is tighter.

Taking this further, just like we now have an abstract concept of "parallel", we
can also have an abstract concept of "perpendicular" or "orthogonal" by
considering when the inequality is as far away as it can be; in other words,
when $`\langle\bm x, \bm y\rangle = 0`$.  This relation defines "orthogonality".

Geometrically in Euclidean vectors, the distance you have gone along one vector
does not affect how far you have gone along another vector which is orthogonal
to it.  No matter how far up the $`y`$-axis you go, your $`x`$-position doesn't
change, but the closest point to the line $`y = x`$ (which is not at right
angles to the $`y`$-axis) does. Similarly, when we come to Fourier expansions,
we will see how the amount of one function you use for your expansion does not
affect how much of the orthogonal functions you use.

Let's consider finite, continuous functions defined on the interval $`[-a, a]`$.
There are several possibilities for an inner product, but the most useful for us
uses integration:

\[
    \langle f,g\rangle = \int_{-a}^a f(x) g(x)\,\mathrm dx.
\]

You might be able to spot this type of operation in the definition of the
Fourier series above!


## Orthogonal bases

This last topic isn't really _new_, it's just a combination of what we've
already defined.  A "basis" (plural "bases" pronounced "bay-sees") is a
subset of the vectors in a vector space that can be used to create any
other vector by addition and scalar multiplication, but you can't make any of
the basis vectors by a similar combination of the others.  A basis is not
unique.  A familiar basis from 3D Euclidean vectors is the set
$`\{\bm i,\,\bm j,\,\bm k\}`$.

The property that basis vectors can't be combinations of the other basis vectors
is called "linear independence", and it implies that when you have a vector
space with a finite number of dimensions (like the Euclidean vectors), every
possible basis contains the same number of elements.  If we have a basis whose
elements are called $`\{\bm x_1,\,\bm x_2,\,\dotsc,\,\bm x_n\}`$, then any other
vector $`\bm y`$ can be written as some

\[
    \bm y = \sum_n c_n \bm x_n,
\]

for scalars $`c_n`$.

It is general useful to consider only bases where every element is orthogonal to
every other element.  The $`\{\bm i,\,\bm j,\,\bm k\}`$ basis above is also an
example of this in its vector space.  These bases are called (imaginatively)
"orthogonal bases".

These concepts of "orthogonality" and a vector-space "basis" are all we need to
define a whole family of series expansions.  The [next article in this
series][part2] will cover that, and then we'll moved on to comparing the
different series expansions we find.

[inner-product]: https://en.wikipedia.org/wiki/Inner_product_space
[cauchy-schwarz]: https://en.wikipedia.org/wiki/Cauchy%E2%80%93Schwarz_inequality

---

This article is the first part of a series.  You can find all of the rest of
the articles in this series here:

- [Part 0: Introduction to Series Expansions][part0]
- [Part 1: Linear Algebra Basics][part1]
- [Part 2: Making Series Expansions From Orthogonal Polynomials][part2]
- [Part 3: Comparing Different Series Expansions][part3]

[part0]: ${article_404ffd}
[part1]: ${article_080743}
[part2]: ${article_ce0047}
[part3]: ${article_a02a84}
