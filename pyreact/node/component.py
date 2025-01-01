from types import SimpleNamespace

from .node import Node, to_node
from ..render import push_context, set_next_ref


class Component(Node):

    def __init__(self, render_func, props, children):
        super().__init__(props, children)
        self._render_func = render_func

    def _copy(self, props, children):
        return Component(self._render_func, props, children)

    def _cmp(self, other):
        if not isinstance(other, Component) or self._render_func != other._render_func:
            return 'incompatible'
        elif self._props != other._props or self._children != other._children:
            return 'compatible'
        else:
            return 'equal'

    def _render(self):
        refs = []

        def next_ref():
            ref = SimpleNamespace()
            refs.append(ref)
            return ref

        with set_next_ref(next_ref):
            node = self._get_node()

        state, result = node._render()
        return (tuple(refs), node, state), result

    def _rerender(self, state, result):
        refs, prev_node, state = state
        ref_iter = iter(refs)

        def next_ref():
            try:
                return next(ref_iter)
            except StopIteration:
                raise AssertionError('more refs used than previous render')

        with set_next_ref(next_ref):
            next_node = self._get_node()

        assert next(ref_iter, None) is None, 'less refs used than previous render'

        match next_node._cmp(prev_node):
            case 'equal':
                pass
            case 'compatible':
                with push_context('render'):
                    state, result = next_node._rerender(state, result)
            case 'incompatible':
                with push_context('render'):
                    state, result = next_node._render()

        return (refs, next_node, state), result

    def _get_node(self):
        if self._children:
            props = {**self._props, 'children': self._children}
        else:
            props = self._props
        return to_node(self._render_func(**props))

    def _extract(self, state, result, key):
        if key != 'render':
            raise KeyError(key)
        _, node, state = state
        return node, state, result

    def _inject(self, state, result, key, child_state, child_result):
        if key != 'render':
            raise KeyError(key)
        refs, node, _ = state
        return (refs, node, child_state), child_result


def component(render_func):
    return Component(render_func, {}, ())
