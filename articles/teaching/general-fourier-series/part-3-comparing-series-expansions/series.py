import scipy.special
import scipy.integrate
import numpy as np
import numpy.polynomial


def legendre_series(f, n):
    r"""
    Calculate the terms of the Legendre series expansion of the function
    ..math:`f(x)` with the first ..math:`n_terms` terms.  This will be the
    terms up to but _excluding_ the coefficient of ..math:`P_n(x)`.

    The resultant object can be called like a function to return the value of
    the approximation at values of ..math:`x`.
    """
    if n < 1:
        raise ValueError("'n' must be at least 1.")
    def integrand(x, k):
        return scipy.special.eval_legendre(k, x)*f(x)
    # Approximate the inner product integral for each of the polynomials,
    # including the normalisation factor.  `scipy.integrate.quad` performs
    # numerical integration (also called 'quadrature') until a particular
    # precision goal is reached.
    return np.polynomial.legendre.Legendre(np.array([
        scipy.integrate.quad(integrand, -1, 1, args=(k,))[0] * (k + 0.5)
        for k in range(n)
    ]))


def taylor_coefficient(f, k, a=15):
    r"""
    Calculate the ..math:`k`th coefficient in the Taylor expansion of
    ..math:`f(x)` around the point ..math:`x_0 = 0`.  The first term is
    ..math:`k = 0`, as this is the zeroth-order term.

    ``a`` is a precision factor, and should probably just be left as-is.
    """
    if k == 0:
        return f(0)
    # The standard way of defining Taylor series with derivatives and
    # factorials doesn't play nicely with numerical methods.  This method is
    # based on contour integration (magic).
    scale = np.exp(-a/k)
    return np.exp(a)/k * sum(
        (-1)**n * np.imag(f(scale * np.exp(1j*np.pi*(0.5-n)/k)))
        for n in range(1, k+1)
    )

def taylor_series(f, n, a=15):
    r"""
    Calculate the first ..math:`n` terms of the Taylor series expansion of
    ..math:`f(x)` around the point ..math:`x_0 = 0` up to but excluding the
    term ..math:`x^n`.

    The resultant object can be called like a function to return the value of
    the approximation at values of ..math:`x`.
    """
    if n < 1:
        raise ValueError("'n' must be at least 1.")
    return np.polynomial.Polynomial([
        taylor_coefficient(f, k, a)
        for k in range(n)
    ])


class fourier_series:
    r"""
    Calculate the first ..math:`n` terms of the Fourier series expansion of
    ..math:`f(x)` when mapped to the period ..math:`[-1, 1)`.

    The terms are "numbered" in the order
    ..math::
        a_0, b_1, a_1, b_2, a_2, \dotsc
    This is by analogy to Taylor series; the first term is the constant, then
    the lowest-order odd term, the next-lowest even term, and so on.

    The resultant object can be called like a function to return the value of
    the approximation at values of ..math:`x`.
    """
    def __init__(self, f, n):
        if n < 1:
            raise ValueError("'n' must be at least 1.")
        self._n_a = (n + 1) // 2
        self._n_b = n - self._n_a
        self.a = np.empty((self._n_a,), dtype=np.float64)
        # To keep the labelling clear I store the `b[0] = 0` too.
        self.b = np.empty((self._n_b + 1,), dtype=np.float64)
        self.a[0] = 0.5 * scipy.integrate.quad(f, -1, 1)[0]
        self.b[0] = 0
        def cosint(x, k): return f(x) * np.cos(k*np.pi*x)
        def sinint(x, k): return f(x) * np.sin(k*np.pi*x)
        for k in range(1, self._n_a):
            self.a[k] = scipy.integrate.quad(cosint, -1, 1, args=(k,))[0]
        for k in range(1, self._n_b):
            self.b[k] = scipy.integrate.quad(sinint, -1, 1, args=(k,))[0]

    def __call__(self, xs):
        out = np.zeros_like(xs)
        for k in range(self._n_a):
            out += self.a[k] * np.cos(k*np.pi * xs)
        for k in range(1, self._n_b):
            out += self.b[k] * np.sin(k*np.pi * xs)
        return out


def high_order_polynomial(x):
    return np.polynomial.Polynomial([
        -0.0372875, 0.674885, 1.34898, -12.652, -7.15369, 57.7268,
        8.73373, -104.258, 10.0257, 79.9955, -21.4594, -21.5587, 8.38861,
    ])(x)


def logistic(x):
    return 1 / (1 + np.exp(-5*x))


def lorentzian(x, c=0.2):
    return 1 / (c*np.pi + (x/c)**2)


_FS = {
    'polynomial': high_order_polynomial,
    'logistic': logistic,
    'lorentzian': lorentzian,
}

_SERIES = {
    'taylor': taylor_series,
    'legendre': legendre_series,
    'fourier': fourier_series,
}


if __name__ == '__main__':
    orders = [('low', 5), ('high', 13)]
    series = [taylor_series, legendre_series, fourier_series]
    xs = np.linspace(-1, 1, 201)
    out = np.empty((len(xs), 2+len(orders)*len(_SERIES)), dtype=np.float64)
    fmt = " ".join(["{:+10.6e}"] * out.shape[1])
    for name, f in _FS.items():
        out[:, 0] = xs
        out[:, 1] = [f(x) for x in xs]
        ptr = 2
        for order_name, order in orders:
            for s in series:
                out[:, ptr] = s(f, order)(xs)
                ptr += 1
        with open(name + ".dat", "w") as outf:
            for line in out:
                print(fmt.format(*line), file=outf)
