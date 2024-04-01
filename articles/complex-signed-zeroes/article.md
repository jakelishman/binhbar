[IEEE-754 floats have the concept of a "signed zero"](https://en.wikipedia.org/wiki/Signed_zero); `0.0` has a different bit representation to `-0.0`.
In most cases, `-0.0` behaves the same way as `0.0`, and it compares equal in arithmetic operations.
It becomes more obviously distinct in floating-point operations that involve some form of limiting behaviour.
For example, `x / 0.0` and `x / -0.0` are opposite-signed infinities.

Along with the other IEEE-754 special values, like quiet/signalling NaN and infinities, these sorts of behaviours prevent compilers from making certain mathematical rewrites that would appear to be completely sound in regular arithmetic.
$`-(a-b)`$ in regular arithmetic over the reals can be written as $`b-a`$, and despite floats having a symmetrical range of positive and negative values (unlike two's complement integers), this is an invalid transformation in IEEE-754 arithmetic regardless of whether a symmetric rounding mode is in effect.
In all rounding modes, the problem occurs at `a = b`; all finite IEEE-754 floats satisfy `x - x = 0.0`, therefore `a - b` and `b - a` are both `0.0`, and negating one to make `-0.0` makes it distinct.

In most uses, this is largely a curiosity and has little impact.
It can be useful in general when the only information needed from the result of a long calculation is its sign.
If the result were to underflow, beyond even the subnormal floats, the resulting sign of the zero would still be able to indicate the correct direction.
The signed zero, then, can be thought of as representing the behaviour in the limit.

Where it becomes far more than a curiosity, with major impactful results, is when the signed zero becomes involved in a calculation with a discontinuity at zero.
For real numbers, the most obvious of these is `atan2(y, x)`, which is the floating-point version of $`\arctan(y/x)`$ including the quadrant of the rotation.
Since the float `-0.0` is then interpreted as $`\lim_{x\to0^-} x`$---the limit as $`x`$ approaches zero by becoming less negative---there is a natural distinction between `atan2(0.0, 0.0)` and `atan2(0.0, -0.0)`.
Treating these as being calculated within $`\lim_{y\to0^+}`$, it becomes sensible that `atan2(0.0, 0.0)` would be a zero rotation, while `atan2(0.0, -0.0)` approximates $`\pi`$.


## Discontinuities with complex signed zeroes

When moving to *complex numbers*, discontinuities become far more common in even elementary operations.
Of particular interest to me recently was a problem we encountered in Qiskit, when moving some of our heavy [two-qubit Weyl decomposition code to Rust](https://github.com/Qiskit/qiskit/pull/11946).
This involved changing the numerics library we were using to drive the code from NumPy to a Rust-based one.
We are currently trialling [a relatively new library called `faer`](https://docs.rs/faer/latest/faer/) in Rust for this.
We need to calculate the determinant of a matrix, then take its fourth root.
In some cases, NumPy would return the determinant in the form `complex(0.0, im)` and `faer` would give us `complex(-0.0, im)`, where they agreed (up to floating-point tolerance) on the value of the imaginary component `im`.
Unfortunately, this is where discontinuities strike once again, but in a far more powerful way.

Exponentiation in complex floating-point arithmetic is a multivalued function.
For all practical purposes, however, we have to choose one of the results to be the *principal value*.
Consider a complex number $`z`$.
We can always write

\[
z = r e^{i\phi}\quad\text{with $r \ge 0$ and $\phi \in (-\pi, \pi]$},
\]

but in fact any $`\phi' = \phi + 2\pi k`$ for integer $`k`$ results in the same complex number.
Exponentiating

\[
z^a = r^a e^{i a(\phi + 2\pi k)},
\]

we can now see that if $`\lvert a \rvert < 1`$, there is more than one possible value of $`k`$ that keeps the argument in our $`(-\pi, \pi]`$ range.
Conventionally, then, we say that the principal value of $`r^a`$ is the positive real value (since $`r`$ was real), which we combine with choosing the argument having $`k = 0`$ to form the principal value of $`z^a`$.

For complex roots, that is the exponent $`a`$ satisfies $`\lvert a \rvert < 1`$, the principal value is the one with the smallest-magnitude argument whose sign matches the sign of the argument of $`z`$.
The argument of $`z`$ similarly has a discontinuity, and it is typically defined for consistency in programming by using `atan2(z.imag, z.real)`.
This results in a branch cut for complex powers along the line $`\operatorname{Im}(z) = 0`$, which brings us back to the signed zero.

In most (if not all) programming languages, the result of `sqrt(complex(-1.0, 0.0))` will be different to `sqrt(complex(-1.0, -0.0))`, because of this branch cut.
Mathematically, this is not a problem and is not incorrect, but when it appears as part of complicated decomposition code, these large-magnitude changes can cause huge cascading effects, causing entirely different decompositions to be chosen.
The resulting decompositions are also valid, but it certainly can cause us headaches while trying to refactor numerical code!

If it's really desired, we can use one of the tricks of IEEE-754 floats that stymies optimising compilers to normalise floating-point zeros to positive branchlessly.
IEEE-754 defines $`x + (-x) = 0`$ for all finite $`x`$, so the statement `x = x + 0.0` leaves all regular values of `x` completely in tact, but negative zeroes are made positive.


## Complex-number literals

Some languages have a literal syntax for working with complex numbers:

* Python uses a `j` suffix on numeric literals;
* Ruby uses an `i` suffix on numeric literals;
* Julia uses an `im` built-in variable in conjunction with its juxtaposition rules for implicit multiplication, so `4im` is interpreted as `4 * im`.
* C99 onwards defines the name `_Complex_I`, which is exactly equivalent to Julia's `im`, but C has no implicit multiplication by juxtaposition so you do `2.0 * _Complex_I`[^1].
* C++14 onwards defines a literal `i` suffix in `std::complex_literals` that is functionally equivalent to Python's `j`.

[^1]:
    We actually usually use `I` in C99 which is _usually_ exactly the same as `_Complex_I`.
    C also describes an optional `_Imaginary` type in its Annex G, though, which has yet another set of rules, and if this is implemented, then `I` is defined to be `_Imaginary_I` instead.
    In practice, neither GCC nor Clang implement Annex G, though some other compilers now do; Annex G was lifted from "informative" status in C99 to "normative" in C11, but remained optional to actually implement.

Notably, all of these methods produce numbers of the form `complex(0.0, b)`; they all start with zero real part.
These languages all allow interoperation between different numeric types, via different mechanisms, so expressions such as `1.0 + 2.0j` (Python) or `1.0 + 2.0im` (Julia) both produce valid complex numbers.

Python and Ruby both promote numeric values of different types to a common type before performing arithmetic operations.
This means that evaluation of the expression `1.0 + 2.0j` is evaluated identically to `add(complex(1.0, 0.0), complex(0.0, 2.0))`.
The expression is not a single complex-number literal, but instead, the real component `1.0` is promoted to a `complex`, then the two components are added together with the rule `complex(a.real + b.real, a.imag + b.imag)`.

C, C++ and Julia behave differently to Python and Ruby.
All three _often_ promote to a common type before arithmetic operations, but not entirely if one operand is a real type and the other is a complex.
C defines its "usual arithmetic conversions" (C99 §6.3.1.8) as finding a "common real type" (_not_ a "common type"), then addition is performed with the values without having promoted any real to a complex.
C++ and Julia have similar behaviour for (at least) the addition and subtraction operators.

It's easiest to see this behaviour in Julia's standard library.
It doesn't use its `convert` and `promote` system to effect addition between reals and complexes, but instead uses its multiple-dispatch system to [overload `+(::Real, ::Complex)` (and vice versa)](https://github.com/JuliaLang/julia/blob/v1.10.2/base/complex.jl#L330-L332) to avoid the initial promotion:

```julia
+(x::Real, z::Complex) = Complex(x + real(z), imag(z))
+(z::Complex, x::Real) = Complex(x + real(z), imag(z))
```

and similar for `-` (but with some extra trickery to avoid `x::Bool` causing trouble).

This approach may feel the same as Python's and Ruby's.
What's hiding, though, is that Julia's imaginary components are directly `imag(z)`, whereas in Python and Ruby they would be `imag(z) + 0.0`.
As we saw previously, in floating-point arithmetic, `x + 0.0` is not necessarily the same float as `x`; it normalises negative zero to positive zero.

These rules are why we end up with:

```bash
$ python -q
>>> 1.0-0.0j
(1+0j)
>>> complex(1.0, -0.0)
(1-0j)

$ irb
irb(main):001:0> 1.0-0.0i
=> (1.0+0.0i)
irb(main):002:0> Complex(1.0, -0.0)
=> (1.0-0.0i)

$ julia -q
julia> 1.0-0.0im
1.0 - 0.0im
```

Note that in both Python and Ruby's case, `complex(1.0, 0.0) - complex(0.0, 0.0)` give the same result as the literal version, but in Julia if we explicitly use a promotion or conversion form of subtraction, we lose the signed zero, and get the same behaviour as Python or Ruby:

```julia
julia> -(promote(1.0, 0.0im)...)
1.0 + 0.0im

julia> convert(Complex, 1.0) - 0.0im
1.0 + 0.0im
```

For completeness' sake, a C form:

```c
#include <complex.h>
#include <stdio.h>

int main(int argc, const char *argv[])
{
    double _Complex z = 1.0 - 0.0*_Complex_I;
    printf("(%g, %g)\n", creal(z), cimag(z));
    return 0;
}
```

```bash
$ gcc-13 -std=c99 complex.c -o complex
$ ./complex
(1, -0)
```

The Julia (and C/C++) behaviour is perhaps the less surprising at the end of the day, since adding some real number to a complex value doesn't feel like it should affect the imaginary component.
The unfortunately knock-on effect, though, is that promoting the real value to a complex and then adding it _also_ feels like it should have the same behaviour, but in the latter case we run afoul of signed zeroes, and the former skips them.
