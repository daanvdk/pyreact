from ..tree import Tree
from ..render import render as base_render


async def render(node, session_id):
    script = Tree('script', {
        'src': f'/_pyreact.js?session={session_id}',
        'defer': True,
    }, {})

    async for tree in base_render(node):
        html = Tree('html', {}, {
            ('head',): Tree('head', {}, {}),
            ('body',): Tree('body', {}, {}),
        })
        add_tree(html, (), tree)
        html[0].children[('script',)] = script
        yield html


def add_tree(html, key, tree):
    head, body = html

    if isinstance(tree, str):
        body.children[key] = tree

    elif tree.tag is None:
        for subkey, child in tree.children.items():
            add_tree(html, (*key, *subkey), child)

    elif tree.tag == 'html':
        html.props.extend(tree.props)
        for subkey, child in tree.children.items():
            add_tree(html, (*key, *subkey), child)

    elif tree.tag == 'head':
        head.props.extend(tree.props)
        for subkey, child in tree.children.items():
            add_tree_inner(head, (*key, *subkey), child)

    elif tree.tag == 'body':
        body.props.extend(tree.props)
        for subkey, child in tree.children.items():
            add_tree_inner(body, (*key, *subkey), child)

    else:
        body.children[key] = tree


def add_tree_inner(html, key, tree):
    if isinstance(tree, str) or tree.tag is not None:
        body.children[key] = tree
    else:
        for subkey, child in tree.children.items():
            add_tree_inner(html, (*key, *subkey), child)
