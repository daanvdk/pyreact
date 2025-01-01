const HTTP_TO_WS = { 'http:': 'ws:', 'https:': 'wss:' };

const [, session_id] = /[?&]session=(.*)(?:&|$)/.exec(document.currentScript.src);
const socket = new WebSocket(`${HTTP_TO_WS[window.location.protocol]}//${window.location.host}/${session_id}`);
const root = createTree(document);

function createTree(node) {
    const children = [];
    for (const child of node.childNodes) {
        if (child.nodeType !== Node.DOCUMENT_TYPE_NODE) {
            children.push(createTree(child));
        }
    }
    return { node, children };
}

function createNode(node) {
    if (typeof node === 'string') {
        return document.createTextNode(node);
    }

    const [tag, props, ...children] = node;
    node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
        node.setAttribute(key, value);
    }
    for (const child of children) {
        node.appendChild(createNode(child));
    }
    return node;
}

function getTree(path) {
    let tree = root;
    for (const index of path) {
        tree = tree.children[index];
    }
    return tree;
}

function getPath(node) {
    const stack = [];
    while (node !== document) {
        stack.push(node);
        node = node.parentNode;
    }

    let tree = root;
    const path = [];
    while (stack.length > 0) {
        const node = stack.pop();
        const index = tree.children.findIndex((subtree) => subtree.node === node); 
        path.push(index);
        tree = tree.children[index];
    }

    return path;
}

function handle(event) {
    const path = getPath(event.currentTarget);
    const details = {};
    socket.send(JSON.stringify([event.type, ...path, details]));
}

socket.addEventListener('message', function (event) {
    for (const [action, ...path] of JSON.parse(event.data)) {
        switch (action) {
            case 'create': {
                const node = createNode(path.pop());
                const index = path.pop();
                const tree = getTree(path);
                tree.node.insertBefore(node, tree.node.childNodes[index] ?? null);
                tree.children.splice(index, 0, createTree(node));
            }; break;

            case 'delete': {
                const index = path.pop();
                const tree = getTree(path);
                tree.node.removeChild(tree.children[index].node);
                tree.children.splice(index, 1);
            }; break;

            case 'replace': {
                const node = createNode(path.pop());
                const index = path.pop();
                const tree = getTree(path);
                tree.node.replaceChild(node, tree.node.childNodes[index]);
                tree.children[index] = createTree(node);
            }; break;

            case 'set': {
                const value = path.pop();
                const key = path.pop();
                const tree = getTree(path);
                tree.node.setAttribute(key, value);
            }; break;

            case 'unset': {
                const key = path.pop();
                const tree = getTree(path);
                tree.node.removeAttribute(key);
            }; break;

            default:
                throw new Error(`unknown action: ${action}`);
        }
    }
});

