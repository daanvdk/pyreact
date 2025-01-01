from .node import Node


class Text(Node):

    def __init__(self, content):
        super().__init__({}, ())
        self._content = content

    def _copy(self, props, children):
        assert props == {} and children == ()
        return self

    def _cmp(self, other):
        if isinstance(other, Text) and self._content == other._content:
            return 'equal'
        else:
            return 'incompatible'

    def _render(self):
        return None, self._content

    def _rerender(self, prev_state, prev_result):
        raise RuntimeError('Text cannot rerender')

    def _extract(self, state, result, key):
        raise KeyError(key)

    def _inject(self, state, result, key, child_state, child_result):
        raise KeyError(key)
