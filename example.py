import asyncio

from pyreact import component, h, fragment, use_state, use_callback
from pyreact.web import App


@component
def counter(init_count=0):
    count, set_count = use_state(init_count)

    @use_callback(set_count)
    def increment(e):
        set_count(lambda count: count + 1)

    @use_callback(set_count)
    def decrement(e):
        set_count(lambda count: count - 1)

    return h.div(
        h.button(onclick=decrement)('-'),
        f' count: {count} ',
        h.button(onclick=increment)('+'),
    )


app = App(fragment(
    counter,
    counter(init_count=10),
))
