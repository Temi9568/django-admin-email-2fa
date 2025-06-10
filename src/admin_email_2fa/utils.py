import sys
from typing import Type


def klass_to_string(klass: Type) -> str:
    """
    Convert a class object to its fully qualified string representation.
    Args:
        klass: The class object to convert.

    Returns:
        A string in the format 'module.ClassName'.

    Example:
        >>> klass_to_string(SomeClass)
        'my_module.submodule.SomeClass'
    """
    return f"{klass.__module__}.{klass.__qualname__}"


def klass_from_str(klass_str: str) -> type:
    """
    Retrieve a class object from its fully qualified string representation.

    Args:
        klass_str: The fully qualified class name as a string.

    Returns:
        The class object corresponding to the string.

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the class is not found in the module.

    Example:
        >>> klass_from_str('my_module.submodule.SomeClass')
        <class 'my_module.submodule.SomeClass'>
    """
    mod_str, klass_str = klass_str.rsplit(".", 1)
    if mod_str in sys.modules:
        mod = sys.modules[mod_str]
    else:
        mod = __import__(mod_str, fromlist=[klass_str])
    return getattr(mod, klass_str)
