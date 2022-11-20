Python scoping can be deceptive, especially since it can appear fairly simple at first.
Generally, name resolution starts from an inner-most scope, and proceeds outwards until some outer scope either contains the name, or we run out of scopes to search.
This procedure is familiar to users of many programming languages.
Newcomers from other languages are often surprised that various control-flow constructs like `for` and `with` _don't_ open new scopes, so new variables defined with them are still accessible after the block has completed, but this is relatively simple to accept; Python often seems very permissive.
This post presents a few corners of Python's scoping rules that are more unusual than this, some of which continue to trip me up.


## Bound exceptions don't leak

Control-flow blocks don't open new scopes, so variables first defined within them are accessible after them.
This also applies to `for` loop variables (assuming there's at least one value to be bound) and the bound values from `with` statements.
For example, if we start with no variables defined, then have a loop followed by a print:
```python
for loop_i in range(3):
    loop_j = loop_i + 4
print(loop_i, loop_j)
```
this succeeds, and prints `2 6`.
The variable definitions are dynamic---as with most things in Python---so if the loop was instead over the empty tuple, the last line would fail with a `NameError`.

This is generally well known for loops and contexts.
However, an `except` clause of a `try` block _looks_ similar, and variables declared in an `except` block will be available outside it, but the actual bound exception will not be.
For example:
```python
try:
    x = 0
    raise RuntimeError
except RuntimeError as exc:
    y = 1

print(x)  # Succeeds.
print(y)  # Succeeds.
print(exc)   # NameError: name 'exc' is not defined.
```
In fact, we can use the block to make the exception persist, but only if we assign it to a new name within the block:
```python
try:
    raise RuntimeError
except RuntimeError as outer_exc:
    inner_exc = outer_exc
print(inner_exc)  # Succeeds.
```
This is caused by a special case in the scoping rules that improves garbage collection efficiency.

As an implementation detail, CPython uses a referencing counting garbage collector with a generational cycle detector, where if an object's reference count drops to zero, it is freed immediately.
Reference cycles prevent this, requiring the full cycle-detecting algorithm to run to clear all the objects involved in the cycle, and decrement the references to objects pointed to by the cycle objects.

Once they are bound into an exception handler, exceptions gain a [traceback object](https://docs.python.org/3/reference/datamodel.html#traceback-objects) that contains, among other things, a [frame object representing the current execution frame](https://docs.python.org/3/reference/datamodel.html#frame-objects) and a pointer to a chained traceback object for the next frame, and so on.
This frame object has an `f_locals` attribute, which points to a proxy of the mapping used to look up all names in the inner-most scope (the same object returned by `locals()` called from that scope).
Since the inner-most scope is the exception handler, the exception is in the locals mapping, and so there is a reference loop affecting every variable already defined in the local scope.
Exceptions and exception handlers are common, so the Python language makes a scoping concession in the interests of performance.


## Class bodies introduce a non-enclosing scope

Functions begin new scopes and classes _sort of_ do too, but with several caveats.
Classes do localise the names within them, so
```python
a = 5

class A:
    a = 1
    b = a + 1
```
is valid, and `A.b` will have the value 2, while the name `a` outside the class definition will still be 5.
Tools such as the ergonomic `property` attribute decorators rely on this behaviour; something like
```python
class A:
    def __init__(self):
        self._a = 1

    @property
    def a(self):
        return self._a

    @a.setter
    def a(self, value):
        print(f"setting {a=}")
        self._a = value

    def print_a(self):
        print(self.a)
```
can only function because the value `a.setter` can refer to the property `a` previously defined in the same scope.
We can even see here that the method (now property descriptor) `a` is accessible by name.
Why then must we do `self.a` within `print_a`, not just use the name `a` like in a closure?

This is because Python classes do not produce an "enclosing" scope.
The order of variable lookups is:

1. first the "locals" of the current scope of the current scope are checked;
2. each successive open "enclosing" (function) scope is checked;
3. names at the "global" (module) level are checked;
4. finally, any Python built-in names are checked.

Notably, containing _classes_ are completely skipped in this lookup.
You can see the same behaviour when using the `nonlocal` keyword.
This causes name resolution to skip step one, and jump straight to step two.
Similarly, the `global` keyword skips steps one and two, and jumps to step three.
If a built-in name is shadowed, one can skip to step four by looking up the name in the `builtins` module.

For class methods, it is actually useful for Python's "every method is virtual" paradigm that we do not confuse matters by allowing previously defined methods to be in scope in later ones, as they would be if classes opened the same sort of scope as functions.
Let us take the (invalid) example:
```python
class A:
    def f(self):
        print("hello from class A!")

    def g(self):
        f()  # NameError: name 'f' is not defined.
```
If instead `f` _was_ in scope within `A.g`, we would have two major problems.
First, the "virtual dispatch" on each method could not trigger correctly; the `f` inside `g` would have been resolved when the method's code was read in to refer specifically to `A.f`, so a subclass of `A` could not override it.
Second, the method binding apparatus would not take place.
From within the body of `A`, the name `f` refers to a regular Python function `f`.
It is only functions' implementations of the descriptor protocol, and the instance access `self.f` that causes the function `f` to be turned into a bound method.
Without this, the call `f` inside `A.g` would be missing its `self` argument, so would raise a `TypeError`.

I rarely confuse this scoping rule within class methods and when referring to methods, largely because the reasons in the previous paragraph feel very natural to me.
I am more likely to forget this when working with class-level data attributes, and potentially with ad-hoc lambda functions used to create those attributes.
This leads me on to the last point, and the one that fully inspired this blog post.


## Comprehension expressions scope like nested functions

Comprehensions can be used to create lists, sets, dictionaries and generators, and are generally the most efficient way of doing so for simple collections where the creation of each element is independent of the previous ones.
A classic example is creating the list of even numbers up to some value:
```python
evens = [2 * i for i in range(10)]
```
This could also be written as
```python
evens = []
for i in range(10):
    evens.append(2 * i)
```
We saw at the top of this article that in the second example, the loop variable `i` "leaks" and is available after the loop.
In the example with the list comprehension, however, this does not happen; the variable `i` does not exist after `evens` is created.
This is because all comprehensions introduce a new enclosing scope, as if they were a regular function.

The CPython compiler actually transforms our first example here into something that looks quite like the second at the byte-code level, at least with respect to the list appends.
The actual calculation, however, is all done within a separate execution frame, which is why the variables don't leak.
This is also one of the more subtle incompatible differences between Python 2 and Python 3.
In the former, list comprehensions leaked the variable, but generator comprehensions didn't.
Generators always needed the separate execution frame, so leaking was never a "natural" option, but an optimisation in the compiler for Python 2 led to list comprehensions avoid the frame and leaking the variable.
Guido van Rossum wrote more about this in [a blog post about the history of Python comprehensions](http://python-history.blogspot.com/2010/06/from-list-comprehensions-to-generator.html), around the time of Python 3.1.

Again, this scoping rule alone rarely trips me up.
I _very_ rarely rely on accessing the loop variable after a loop (in these cases, loops over empty iterables can cause you unexpected `NameError` headaches), so it does not matter to me that the loop variable does not leak, other than things being safer since there's no risk of an existing variable getting clobbered.
What does trip me up is that because list comprehensions are enclosing scopes, name-resolution within them skips over containing classes, as in the previous section.
This makes it much harder to use class variables to construct others inside comprehensions.
For example, let's say I want to build up variables:
```python
def process(x, base): ...

class A:
    base = (1, 2, 3)
    processed = [
        process(x, base) for x in (4, 5, 6)  # NameError: name 'base' is not defined
    ]
```
The name `process` can safely be found since it is in the global scope, but from within the pseudo-closure of the list comprehension, the name `base` is neither local, nor in an enclosing scope (as classes don't count), nor in the global scope, nor built in.
The collection of the comprehension (the `(4, 5, 6)`, in this case) is what is "passed in" to the closure of the comprehension; this is eagerly evaluated, and here _could_ be the name `base`.
The value of the comprehension and any conditional expressions are inside the closure, and so cannot reference class variables.

If you desperately want, you can use alternative methods to access the class variables within comprehensions.
A common trick when defining closures within loops is to use the eager evaluation of keyword-argument defaults to defeat the lazy evalation of closed-over loop variables.
For example
```python
bad_adders = [(lambda x: x + i) for i in range(4)]
```
actually produces four closure that all add three to their input, whereas
```python
good_adders = [(lambda x, i=i: x + i) for i in range(4)]
```
is far closer to what is (usually) intended, because the keyword-default binding `i=i` in the `lambda` evaluates the outer-scope `i` and stores it in the `__defaults__` tuple of each lambda in turn.
Since `lambda` introduces an enclosing scope, we can push the class variable into the comprehension with a similar trick:
```python
class A:
    base = (1, 2, 3)
    reordered = (lambda base: [base[i] for i in (2, 0, 1)])(base)
    # ... or ...
    reordered = (lambda base=base: [base[i] for i in (2, 0, 1)])()
```
Of course, neither of these are probably sensible to include in _real_ code, but it's interesting to see what we can do when we properly understand the scoping rules.
