import asyncio
from contextvars import ContextVar, copy_context
from contextlib import contextmanager

from .node import to_node


CONTEXT = ContextVar('context')


class Context:

    def __init__(self):
        self.path = None
        self.next_ref = None
        self.rerender_paths = set()
        self.rerender_event = asyncio.Event()

        token = CONTEXT.set(self)
        try:
            self.ctx = copy_context()
        finally:
            CONTEXT.reset(token)

    def run(self, path, /, *args, **kwargs):
        assert self.path is None
        self.path = path
        try:
            return self.ctx.run(*args, **kwargs)
        finally:
            self.path = None

    def rerender(self, path):
        self.rerender_paths.add(path)
        self.rerender_event.set()
        self.rerender_event.clear()


@contextmanager
def push_context(key):
    context = CONTEXT.get()
    context.path.append(key)
    try:
        yield
    finally:
        context.path.pop()


@contextmanager
def set_next_ref(next_ref):
    context = CONTEXT.get()
    assert context.next_ref is None
    context.next_ref = next_ref
    try:
        yield
    finally:
        context.next_ref = None


async def render(node):
    node = to_node(node)
    context = Context()

    state, result = context.run([], node._render)

    while True:
        yield result
        await context.rerender_event.wait()

        stack = []

        for path in sorted(context.rerender_paths):
            while stack and (len(stack) > len(path) or stack[-1][0] != path[len(stack) - 1]):
                key, node, pstate, presult = stack.pop()
                state, result = node._inject(pstate, presult, key, state, result)

            for key in path[len(stack):]:
                stack.append((key, node, state, result))
                node, state, result = node._extract(state, result, key)

            state, result = context.run(list(path), node._rerender, state, result)

        while stack:
            key, node, pstate, presult = stack.pop()
            state, result = node._inject(pstate, presult, key, state, result)

        context.rerender_paths.clear()