import html
from collections import namedtuple, Counter
from collections.abc import Sequence


class Tree(Sequence):

    def __init__(self, tag, props, children):
        self.tag = tag
        self.props = props
        self.children = children

    def __str__(self):
        return ''.join(to_html(self))

    def __iter__(self):
        for _, tree in merge_text(flatten_children(self.children)):
            yield tree

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.props[key]

        children = iter(self)
        try:
            for _ in range(key):
                next(children)
            tree = next(children)
        except StopIteration:
            raise IndexError() from None
        return tree

    def __len__(self):
        res = 0
        for _ in self:
            res += 1
        return res


SELF_CLOSING = {
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
}


def to_html(tree):
    if isinstance(tree, str):
        yield html.escape(tree, quote=False)
        return

    if tree.tag is None:
        assert not tree.props
        for child in tree.children.values():
            yield from to_html(child)
        return

    yield '<'
    yield tree.tag

    for key, value in clean_props(tree.props).items():
        yield ' '
        yield key
        if value:
            yield '="'
            yield html.escape(value)
            yield '"'

    if tree.tag in SELF_CLOSING:
        assert not tree.children
        yield ' />'
    else:
        yield '>'
        for child in tree.children.values():
            yield from to_html(child)
        yield '</'
        yield tree.tag
        yield '>'


def clean_props(props):
    cleaned = {}

    for key, value in props.items():
        if key == 'key' or value is False:
            continue
        elif value is True:
            value = ''
        cleaned[key] = str(value)

    return cleaned


def flatten_children(children, path=()):
    for key, child in children.items():
        if isinstance(child, str) or child.tag is not None:
            yield (*path, *key), child
        else:
            yield from flatten_children(child.children, (*path, *key))


def merge_text(children):
    text_parts = []
    text_counter = Counter()

    def clear_text():
        if not text_parts:
            return

        text = ''.join(text_parts)
        text_parts.clear()
        yield ('text', text_counter[text]), text
        text_counter[text] += 1

    for key, child in children:
        if isinstance(child, str):
            text_parts.append(child)
        else:
            yield from clear_text()
            yield key, child

    yield from clear_text()


def diff(old_tree, new_tree):
    return diff_children((), {(): old_tree}, {(): new_tree})


def diff_children(path, old_children, new_children):
    old_children = list(merge_text(flatten_children(old_children)))
    new_children = list(merge_text(flatten_children(new_children)))
    new_children_by_key = dict(new_children)

    old_i = 0
    deletes = 0

    for new_i, (key, new_child) in enumerate(new_children):
        # First get rid of nodes that are at the current position that we will
        # not use for diffing
        while old_i < len(old_children):
            key_, old_child = old_children[old_i]
            try:
                diffable = is_diffable(old_child, new_children_by_key[key_])
            except KeyError:
                diffable = False
                
            if diffable:
                break

            deletes += 1
            old_i += 1

        # Then check if we can find a node to diff with
        for cur_i in range(old_i, len(old_children)):
            key_, old_child = old_children[cur_i]
            if key_ == key:
                diffable = is_diffable(old_child, new_child)
                break
        else:
            diffable = False

        # Check if we can diff with node, otherwise just create
        if not diffable:
            if deletes:
                action = 'replace'
                deletes -= 1
            else:
                action = 'create'

            yield (action, *path, new_i, to_node(new_child))
            continue

        # Handle deletes so we can diff
        while deletes:
            yield ('delete', *path, new_i)
            deletes -= 1

        # Check if we have to move the node to the current position first
        if cur_i > old_i:
            yield ('move', *path, new_i + (cur_i - old_i), new_i)
            old_children.insert(old_i, old_children.pop(cur_i))

        # Diff the nodes if they are trees
        if not isinstance(new_child, str) and old_child is not new_child:
            old_props = clean_props(old_child.props)
            for key, new_value in clean_props(new_child.props).items():
                if new_value != old_props.pop(key, None):
                    yield ('set', *path, new_i, key, new_value)
            for key in old_props:
                yield ('unset', *path, new_i, key)
            yield from diff_children((*path, new_i), old_child.children, new_child.children)

        old_i += 1
           
    # Delete all remaining old nodes
    for _ in range(deletes + len(old_children) - old_i):
        yield ('delete', *path, len(new_children))


def to_node(tree):
    if isinstance(tree, str):
        return tree
    else:
        return (
            tree.tag,
            clean_props(tree.props),
            *map(to_node, tree.children.values()),
        )

    
def is_diffable(old_tree, new_tree):
    if isinstance(new_tree, str):
        return old_tree == new_tree
    else:
        return not isinstance(old_tree, str) and old_tree.tag == new_tree.tag



