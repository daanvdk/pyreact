from collections import Counter
from contextvars import copy_context
from functools import partial

from .node import Node
from .text import Text
from ..render import push_context, CONTEXT
from ..tree import Tree


class Element(Node):

    def __init__(self, tag, props, children):
        super().__init__(props, children)
        self._tag = tag

    def _copy(self, props, children):
        return Element(self._tag, props, children)

    def _cmp(self, other):
        if not isinstance(other, Element) or self._tag != other._tag:
            return 'incompatible'
        elif self._props != other._props or self._children != other._children:
            return 'compatible'
        else:
            return 'equal'

    def _render(self):
        return self._rerender({}, {})

    def _rerender(self, prev_state, prev_result):
        prev_state = prev_state.copy()
        next_state = {}
        next_children = {}
        key_counter = Counter()

        props = {}
        for key, value in self._props.items():
            if callable(value) and not isinstance(value, Callback):
                value = Callback(value)
            props[key] = value

        for child in self._children:
            if isinstance(child, Text):
                base_key = ('text', child._content)
            else:
                try:
                    base_key = ('key', child._props['key'])
                except KeyError:
                    base_key = ('no_key',)

            key = (*base_key, key_counter[base_key])
            key_counter[base_key] += 1

            try:
                prev_child, state = prev_state.pop(key)
            except KeyError:
                cmp = 'incompatible'
            else:
                result = prev_result.children[key]
                cmp = child._cmp(prev_child)
                if cmp == 'incompatible':
                    with push_context(key):
                        prev_child._unmount(state, result)
                        context = CONTEXT.get()
                        context.rerender_paths.poptree(context.path)

            match cmp:
                case 'equal':
                    pass
                case 'compatible':
                    with push_context(key):
                        state, result = child._rerender(state, result)
                case 'incompatible':
                    with push_context(key):
                        state, result = child._render()

            next_state[key] = child, state
            next_children[key] = result

        for key, (prev_child, state) in prev_state.items():
            result = prev_result.children[key]
            with push_context(key):
                prev_child._unmount(state, result)
                context = CONTEXT.get()
                context.rerender_paths.poptree(context.path)

        next_result = Tree(self._tag, props, next_children)
        return next_state, next_result

    def _unmount(self, state, result):
        for key, (child, child_state) in state.items():
            child_result = result.children[key]
            with push_context(key):
                child._unmount(child_state, child_result)

    def _extract(self, state, result, key):
        node, state = state[key]
        result = result.children[key]
        return node, state, result

    def _inject(self, state, result, key, child_state, child_result):
        node, _ = state[key]
        state = {**state, key: (node, child_state)}
        result = Tree(result.tag, result.props, {**result.children, key: child_result})
        return state, result


class ElementFactory:

    def __getattr__(self, name):
        return Element(name, {}, ())

    def __getitem__(self, name):
        return Element(name, {}, ())


class Callback:

    def __init__(self, callback):
        if isinstance(callback, Callback):
            self.callback = callback.callback
            self.context = callback.context
            self.prevent_default = callback.prevent_default
            self.stop_propagation = callback.stop_propagation
        else:
            self.callback = callback
            self.context = copy_context()
            self.prevent_default = False
            self.stop_propagation = False

    def __str__(self):
        return f'handle(event,{int(self.prevent_default)},{int(self.stop_propagation)})'

    def __call__(self, *args, **kwargs):
        return self.context.run(self.callback, *args, **kwargs)


def prevent_default(callback):
    callback = Callback(callback)
    callback.prevent_default = True
    return callback


def stop_propagation(callback):
    callback = Callback(callback)
    callback.stop_propagation = True
    return callback


h = ElementFactory()
fragment = Element(None, {}, ())
