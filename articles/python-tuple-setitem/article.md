Tuples are as immutable as things get in Python.
They have special treatment being a core builtin, so unlike user-defined classes, there's no private attribute that you can mutate if you really want to mess around.
However, Python is an interpreted language with no baked-in access control, and (almost) everything really is mutable if you try hard enough.

All Python objects at the C level can be addressed by a pointer of type `PyObject *`, which (for most regular CPython builds) has the elements
```c
struct _object {
    Py_ssize_t ob_refcnt;
    PyTypeObject *ob_type;
}
```
These objects do what they say on the tin.
The different types of C object then have further elements after these, to specialise them.

Tuples are a type of "variable-length" object, in the sense that the same C struct definition is used for all sizes.
With the head components inlined, this looks like
```c
struct _tuple {
    Py_ssize_t ob_refcnt;
    PyTypeObject *ob_type;
    Py_ssize_t ob_size;
    PyObject *ob_item[1];
}
```
The first two arguments are the reference count and the Python type object, as before, then the next is the number of elements in the tuple, and the last one is an array of (pointers to) Python objects.
The array is declared as size one, but Python guarantees that enough space will actually have been allocated to hold `ob_size` elements.
The items in the tuple are stored in this array.

From Python space, `tuple.__setitem__` raises a `TypeError`, but in principle at the C level, there is no such immutability.
As of Python 3.11, the `tupleobject.h` header file even [has a comment explaining how `tuple` can be used as a temporary array](https://github.com/python/cpython/blob/3.11/Include/tupleobject.h#L9-L21), and there is a [`PyTuple_SetItem` function implementation](https://github.com/python/cpython/blob/92b531b8589b733c4e44e291f08271fa34947400/Objects/tupleobject.c#L111-L129), although this has slightly different reference-counting semantics to normal.

We can use the [Python C FFI `ctypes`](https://docs.python.org/3.11/library/ctypes.html), and the CPython implementation detail that [`id` returns the memory address of the Python object](https://docs.python.org/3.11/library/functions.html#id) to cheekily define our own Python-space `tuple_setitem`.
The `PyObject` type in `ctypes` doesn't expose the internal fields of the object, but instead we can change the items we want by casting the integer output of `id` into an `size_t` (assuming, as in many systems that pointers have the same size as `size_t`), and manually assigning into the `ob_item` array.
To be better citizens of Python---rampant pointer abuse aside---we should also increment the reference count of the object we are inserting into the tuple, and decrement the count for the object we are removing.
This leaves us with the Python-space function
```python
from ctypes import cast, c_size_t, c_ssize_t, POINTER
from typing import Any

def tuple_setitem(tup: tuple, index: int, new: Any):
    if -len(tup) <= index < 0:
        index = len(tup) + index
    if not 0 <= index < len(tup):
        raise IndexError("tuple index out of range")

    # Decrement the old item's refcount.
    old = tup[index]
    cast(id(old), POINTER(c_ssize_t))[0] -= 1

    # Increment the new item's refcount.
    cast(id(new), POINTER(c_ssize_t))[0] += 1

    # Replace the item.
    cast(id(tup), POINTER(c_size_t))[3 + index] = id(new)
```
Now let's try it out:
```python
>>> tup = (1, 2, 3)
>>> tuple_setitem(tup, 0, 7)
>>> tup
(7, 2, 3)
```

In this implementation of `tuple_setitem` on line 11, we deliberately pulled out a Python-space reference to the old item.
This increases the reference count by one, which is dropped at the end of the function.
I did this deliberately, so the regular CPython update mechanism will be the code responsible for making a reference hit zero, if this was the last reference, which will trigger the eager garbage collection rather than requiring a full collection at a later time to recognise the loose item.

There is a limitation here, that we still cannot change the size of the tuple.
The array is allocated immediately following the header of the struct, and since we cannot allow the struct to move in memory, we cannot safely `realloc` the array only.
This shows another fundamental difference between `list` and `tuple`; in `tuple`, the contained (pointers to) Python objects are local to the rest of the `PyObject`, but in `list`, the container is itself a pointer to elsewhere on the heap, to allow the size to grow over time without the memory location of the `list` itself changing.

Of course, mutating tuples breaks various parts of the Python data model, and this should never be used in practice.
Still, however, it goes to show that (almost) everything in Python is mutable, if you try hard enough.
