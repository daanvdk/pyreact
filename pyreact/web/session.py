import asyncio
from contextvars import ContextVar
from collections import Counter
from uuid import uuid4

from ..render import CONTEXT
from ..hooks import use_ref, use_callback
from ..node import component, h, prevent_default


SESSION = ContextVar('session')


class Session:

    def __init__(self, scope):
        self.id = str(uuid4())

        self.actions = []
        self.actions_event = asyncio.Event()

        self._context = None
        self.url = scope['path']
        self.url_paths = Counter()

    @property
    def context(self):
        if self._context is None:
            self._context = CONTEXT.get()
        return self._context

    def replace_url(self, url):
        self.set_url(url)
        self.append_action(('replace_url', url))

    def push_url(self, url):
        self.set_url(url)
        self.append_action(('push_url', url))

    def append_action(self, action):
        self.actions.append(action)
        self.actions_event.set()
        self.actions_event.clear()

    def set_url(self, url):
        self.url = url
        for url in self.url_paths:
            self.context.rerender(url)
        

def get_url():
    return SESSION.get().url


def push_url(url):
    SESSION.get().push_url(url)


def replace_url(url):
    SESSION.get().replace_url(url)


def use_url():
    session = SESSION.get()
    ref = use_ref()

    if not hasattr(ref, 'cleanup'):
        path = tuple(session.context.path)
        session.url_paths[path] += 1

        def cleanup():
            session.url_paths[path] -= 1
            if not session.url_paths[path]:
                del session.url_paths[path]

        ref.cleanup = cleanup

    return session.url
        

@component
def link(href, children=(), **props):
    @use_callback(href)
    @prevent_default
    def handle_click(e):
        push_url(href)
    return h.a(*children, href=href, onclick=handle_click, **props)
