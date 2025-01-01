from collections import Counter

from .node import Node
from .text import Text
from ..render import push_context
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
        next_state = {}
        next_children = {}
        key_counter = Counter()

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
                prev_child, state = prev_state[key]
            except KeyError:
                cmp = 'incompatible'
            else:
                result = prev_result.children[key]
                cmp = child._cmp(prev_child)

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

        next_result = Tree(self._tag, self._props, next_children)
        return next_state, next_result

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


h = ElementFactory()
fragment = Element(None, {}, ())
