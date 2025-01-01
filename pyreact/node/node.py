from abc import ABC, abstractmethod
from collections.abc import Mapping


class Node(ABC):

    def __init__(self, props, children):
        assert 'children' not in props
        self._props = props
        self._children = tuple(map(to_node, children))

    def __call__(self, *args, **kwargs):
        props = dict(self._props)
        children = list(self._children)

        for arg in args:
            if isinstance(arg, Mapping):
                props.update(arg)
            else:
                children.append(arg)

        props.update(kwargs)

        return self._copy(props, children)

    def __eq__(self, other):
        return self._cmp(other) == 'equal'

    @abstractmethod
    def _copy(self, props, children):
        raise NotImplementedError

    @abstractmethod
    def _cmp(self, other):
        raise NotImplementedError

    @abstractmethod
    def _render(self):
        raise NotImplementedError

    @abstractmethod
    def _rerender(self, props, children):
        raise NotImplementedError

    @abstractmethod
    def _extract(self, state, result, key):
        raise NotImplementedError

    @abstractmethod
    def _inject(self, state, result, key, child_state, child_result):
        raise NotImplementedError


def to_node(value):
    from .text import Text
    from .element import Element

    if isinstance(value, Node):
        return value

    if isinstance(value, str):
        return Text(value)

    if value is None or value is False:
        return Element(None, {}, ())

    try:
        subvalues = iter(value)
    except TypeError:
        pass
    else:
        return Element(None, {}, subvalues)

    return Text(repr(value))
