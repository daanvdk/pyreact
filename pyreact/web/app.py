import asyncio
import json
from uuid import uuid4
from pathlib import Path
from mimetypes import guess_type
from types import SimpleNamespace

from ..node import to_node
from ..tree import Tree, diff
from .render import render
from .session import Session, SESSION


SCRIPT_PATH = Path(__file__).parent / 'app.js'
CHUNK_SIZE = 4096


class App:

    def __init__(self, node):
        self._node = to_node(node)
        self._sessions = {}

    async def __call__(self, scope, receive, send):
        return await getattr(self, scope['type'])(scope, receive, send)

    async def http(self, scope, receive, send):
        if scope['path'] == '/_pyreact.js':
            return await self.http_file(scope, receive, send, SCRIPT_PATH)

        session = Session(scope)
        token = SESSION.set(session)
        try:
            trees = render(self._node, session.id)
            tree = await anext(trees)
        finally:
            SESSION.reset(token)

        self._sessions[session.id] = session, tree, trees

        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b'content-type', b'text/html; charset=utf-8')],
        })
        await send({
            'type': 'http.response.body',
            'body': f'<!doctype html>{tree}'.encode(),
        })

    async def http_file(self, scope, receive, send, path):
        if not path.is_file():
            await send({
                'type': 'http.response.start',
                'status': 404,
                'headers': [(b'content-type', b'text/plain; charset=utf-8')],
            })
            await send({
                'type': 'http.response.body',
                'body': b'File not found',
            })
            return

        headers = []

        content_type, encoding = guess_type(path)
        if content_type is not None:
            headers.append((b'content-type', content_type.encode()))
        if encoding is not None:
            headers.append((b'content-encoding', encoding.encode()))

        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': headers,
        })
        with path.open('rb') as f:
            more_body = True
            while more_body:
                chunk = f.read(CHUNK_SIZE)
                more_body = len(chunk) == CHUNK_SIZE
                await send({
                    'type': 'http.response.body',
                    'body': chunk,
                    'more_body': more_body,
                })

    async def websocket(self, scope, receive, send):
        assert (await receive())['type'] == 'websocket.connect'

        session_id = scope['path'][1:]
        try:
            session, node, nodes = self._sessions.pop(session_id)
        except KeyError:
            await send({'type': 'websocket.close'})
            return

        await send({'type': 'websocket.accept'})
            
        receive_fut = asyncio.create_task(receive())
        actions_fut = asyncio.create_task(session.actions_event.wait())
        node_fut = asyncio.create_task(anext(nodes))

        try:
            while True:
                await asyncio.wait(
                    {receive_fut, actions_fut, node_fut},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if receive_fut.done():
                    message = receive_fut.result()
                    if message['type'] == 'websocket.disconnect':
                        break

                    assert message['type'] == 'websocket.receive'
                    event_type, *path, data = json.loads(
                        message.get('bytes') or
                        message.get('text') or
                        b''
                    )

                    if event_type == 'pop_url':
                        assert not path
                        session.set_url(data)
                    else:
                        target = Tree(None, {}, {(): node})
                        for index in path:
                            target = target[index]
                        handler = target.props[f'on{event_type}']
                        event = SimpleNamespace(type=event_type, **data)
                        asyncio.get_running_loop().call_soon(handler, event)

                    receive_fut = asyncio.create_task(receive())

                actions = []

                if actions_fut.done():
                    actions.extend(session.actions)
                    session.actions.clear()
                    actions_fut = asyncio.create_task(session.actions_event.wait())

                if node_fut.done():
                    new_node = node_fut.result()
                    actions.extend(diff(node, new_node))
                    node = new_node
                    node_fut = asyncio.create_task(anext(nodes))

                if actions:
                    await send({
                        'type': 'websocket.send',
                        'text': json.dumps(actions, separators=(',', ':')),
                    })

        finally:
            receive_fut.cancel()
            node_fut.cancel()
