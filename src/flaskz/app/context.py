"""
Framework-independent execution context.

Provides request/task scoped data storage based on ContextVar.
It can be used with Flask, FastAPI, scripts and background tasks.

Async tasks inherit the current context stack. Because the stack
contains mutable dictionaries, a child task shares the inherited
current context unless it calls begin_context() to create a new one.

.. versionadded:: 1.9.1

"""

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from uuid import uuid4

_context_stack_var = ContextVar('flaskz_context_stack', default=())


def begin_context(values=None, *, context_key=None):
    """

    Create and activate a new execution context.

    If context_key is not specified, a unique key is generated.
    Duplicate context keys within the current context stack are not allowed.

    :param values: Optional initial context values, shallow-copied when supplied as a dictionary.
    :param context_key: Optional context key.

    :return: Context key.

    :raises ValueError: If the context key already exists.
    """

    stack = _context_stack_var.get()
    if context_key is None:
        context_key = uuid4().hex

    if _find_context_index(stack, context_key) >= 0:
        raise ValueError(f"Context already exists: {context_key!r}")

    context = {
        'values': dict(values) if isinstance(values, dict) else {},
        'options': {},
        'cleanup': ExitStack(),
    }

    _context_stack_var.set(stack + ((context_key, context),))
    return context_key


def end_context(*, context_key=None):
    """
    End an execution context and execute registered cleanup callbacks.

    If context_key is None, the current (topmost) context is removed.
    Otherwise, the specified context is removed from the stack.

    Registered cleanup callbacks execute in reverse registration order.
    Other contexts remain unaffected.

    :param context_key: Context identifier. None selects the current context.
    :return: True if a context was removed, otherwise False.
    """
    stack = _context_stack_var.get()
    index = _find_context_index(stack, context_key)
    if index < 0:
        return False
    context = stack[index][1]
    try:
        context['cleanup'].close()
    finally:
        # Remove the specified context while preserving other contexts.
        stack = _context_stack_var.get()
        for index, (_, item) in enumerate(stack):
            if item is context:
                _context_stack_var.set(stack[:index] + stack[index + 1:])
                break
    return True


def register_context_cleanup(callback, *args, context_key=None, **kwargs):
    """
    Register a cleanup callback for the specified context.

    Callbacks execute in reverse registration order when the
    context ends.

    :param callback: Cleanup function.
    :param args: Positional arguments passed to callback.
    :param context_key: Optional context key.
    :param kwargs: Keyword arguments passed to callback.
    :return: True if registered, otherwise False.
    """
    context = _get_context(context_key=context_key)
    if context is None:
        return False

    if not callable(callback):
        raise TypeError('Cleanup callback must be callable')

    context['cleanup'].callback(callback, *args, **kwargs)
    return True


def has_context(*, context_key=None):
    """
    Check whether an execution context exists.

    :param context_key: Context identifier. None selects the current context.
    :return: True if the context exists, otherwise False.
    """
    stack = _context_stack_var.get()
    return _find_context_index(stack, context_key) >= 0


def _get_context(default=None, *, context_key=None):
    """
    Return the context dictionary containing values, options and cleanup.

    Direct business-data access uses context['values'][key].
    Prefer the value/option helper functions for ordinary access.

    This function never creates a context.

    :param default: Value returned when the context does not exist.
    :param context_key: Context identifier. None selects the current context.
    :return: Context dictionary or default.
    """
    stack = _context_stack_var.get()
    index = _find_context_index(stack, context_key)
    return stack[index][1] if index >= 0 else default


def get_context_key():
    """
    Get the current (topmost) execution context key.

    :return: Context key or None if no context exists.
    """
    stack = _context_stack_var.get()
    return stack[-1][0] if stack else None


def has_context_value(key, *, context_key=None):
    """
    Check whether a key exists in an execution context.

    This function never creates a context.

    :param key: Context value key.
    :param context_key: Context identifier. None selects the current context.
    :return: True if the key exists, otherwise False.
    """
    context = _get_context(context_key=context_key)
    return context is not None and key in context['values']


def get_context_value(key, default=None, *, context_key=None):
    """
    Retrieve a value from an execution context.
    This function never creates a context.

    :param key: Context value key.
    :param default: Value returned when the key or context does not exist.
    :param context_key: Context identifier. None selects the current context.

    :return: Context value or default.
    """
    context = _get_context(context_key=context_key)
    return default if context is None else context['values'].get(key, default)


def get_context_values(*, context_key=None):
    """
    Retrieve all values from an execution context.

    This function never creates a context.
    Control options and cleanup state are excluded from the result.
    A shallow copy is returned to prevent direct modification
    of the context dictionary.

    :param context_key: Context identifier. None selects the current context.
    :return: Dictionary of context values, or an empty dictionary if the context does not exist.
    """
    context = _get_context(context_key=context_key)
    if context is None:
        return {}

    return dict(context['values'])


def set_context_value(key, value, *, context_key=None):
    """
    Store a value in an execution context.
    This function never creates a context.

    :param key: Context value key.
    :param value: Value to store.
    :param context_key: Context identifier. None selects the current context.

    :return: True if stored, False if the context does not exist.
    """
    context = _get_context(context_key=context_key)
    if context is None:
        return False
    context['values'][key] = value
    return True


def set_context_values(values, *, context_key=None):
    """
    Store multiple values in an execution context.

    :param values: Dictionary of context values.
    :param context_key: Context identifier. None selects the current context.
    :return: True if updated, False if the context does not exist.
    """
    context = _get_context(context_key=context_key)
    if context is None:
        return False

    context['values'].update(values)
    return True


def remove_context_value(key, default=None, *, context_key=None):
    """
    Remove and return a value from an execution context.

    :param key: Context value key.
    :param default: Value returned when the key or context does not exist.
    :param context_key: Context identifier. None selects the current context.

    :return: Removed value or default.
    """
    context = _get_context(context_key=context_key)
    return default if context is None else context['values'].pop(key, default)


def clear_context_values(*, context_key=None):
    """
    Remove all values from an execution context.
    The context remains active. Control options and cleanup callbacks are preserved.

    :param context_key: Context identifier. None selects the current context.
    :return: True if cleared, False if the context does not exist.

    """
    context = _get_context(context_key=context_key)
    if context is None:
        return False

    context['values'].clear()

    return True


def get_context_option(key, default=None, *, context_key=None):
    """Get a control option, or default if the option/context is missing."""
    context = _get_context(context_key=context_key)
    return default if context is None else context['options'].get(key, default)


def set_context_option(key, value, *, context_key=None):
    """Set a control option. Return False if the context does not exist."""
    context = _get_context(context_key=context_key)
    if context is None:
        return False
    context['options'][key] = value
    return True


@contextmanager
def context_scope(values=None, *, context_key=None):
    """
    Create a scoped execution context.
    The context is automatically removed when the block exits, including when an exception occurs.
    Only the context created by this scope is removed.

    :param values: Optional initial context dictionary.
    :param context_key: Optional context key.
    :yield: Context key.
    """
    _context_key = begin_context(values, context_key=context_key)
    try:
        yield _context_key
    finally:
        end_context(context_key=_context_key)


# ------------------------------------------- internal-------------------------------------------
def _find_context_index(stack, context_key=None):
    """
    Find the index of a context in the stack.

    :param stack: Context stack.
    :param context_key: Context identifier. None selects the topmost context.
    :return: Context index, or -1 if not found.
    """
    if context_key is None:
        return len(stack) - 1
    for index in range(len(stack) - 1, -1, -1):
        if stack[index][0] == context_key:
            return index
    return -1

if __name__ == '__main__':
    import asyncio


    async def worker(task_id):
        context_key = begin_context({"task_id": task_id})
        try:
            await asyncio.sleep(0.1)
            print(get_context_value("task_id"))
        finally:
            end_context(context_key=context_key)


    async def main():
        await asyncio.gather(
            worker("task-1"),
            worker("task-2")
        )


    asyncio.run(main())