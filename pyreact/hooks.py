from functools import partial

from .render import CONTEXT


def use_ref():
    context = CONTEXT.get()
    return context.next_ref()


def get_rerender():
    context = CONTEXT.get()
    return partial(context.rerender, tuple(context.path))


def use_state(init_value=None):
    ref = use_ref()

    if not hasattr(ref, 'value'):
        if callable(init_value):
            init_value = init_value()

        ref.value = init_value
        rerender = get_rerender()

        def set_value(value):
            if callable(value):
                value = value(ref.value)
            ref.value = value 
            rerender()

        ref.set_value = set_value

    return ref.value, ref.set_value


def use_memo(*key, func=None):
    if func is None:
        return lambda func: use_memo(*key, func=func)

    ref = use_ref()

    if not hasattr(ref, 'key') or ref.key != key:
        ref.key = key
        ref.value = func()

    return ref.value


def use_callback(*key, func=None):
    if func is None:
        return lambda func: use_callback(*key, func=func)

    return use_memo(*key, func=lambda: func)
