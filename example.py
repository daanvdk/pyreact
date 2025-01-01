import asyncio

from pyreact import component, h, fragment, use_state, use_callback
from pyreact.web import App, use_url, link


@component
def hello_world():
    name, set_name = use_state('World')

    @use_callback(set_name)
    def handle_input(e):
        set_name(e.value)

    @use_callback(set_name)
    def handle_reset(e):
        set_name('World')

    return fragment(
        h.div(f'Hello, {name}!'),
        h.input(value=name, oninput=handle_input),
        h.button(onclick=handle_reset)('reset'),
    )


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
        count > 10 and h.p('That\'s high!'),
    )


@component
def not_found():
    url = use_url()
    return f'url not found: {url}'


PAGES = {
    '/': hello_world,
    '/hello-world': hello_world,
    '/counters': fragment(
        counter,
        counter(init_count=10),
    ),
}


@component
def router():
    url = use_url()
    page = PAGES.get(url, not_found)
    return fragment(
        h.ul(
            h.li(link(href='/hello-world')('Hello, World!')),
            h.li(link(href='/counters')('Counters')),
        ),
        page,
    )


app = App(router)
