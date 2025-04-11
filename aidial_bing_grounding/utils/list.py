from typing import List, TypeVar

_T = TypeVar("_T")


def get_last(xs: List[_T]) -> _T:
    """Returns the last element of a list
    >>> get_last([1, 2, 3])
    3
    >>> get_last([1, 2, 3, 4])
    4
    """
    return xs[-1]
