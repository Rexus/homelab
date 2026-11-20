"""Keep native editing/diagram processors subscribed while publishing via HTTP mutations."""

import json
from threading import Event, Thread
import time
import uuid
from urllib.parse import urlsplit, urlunsplit
import websocket


class EditingSession:
    """Use Sirius's documented graphql-ws protocol; always verify persisted results too."""

    def __init__(self, client, context):
        self.client, self.context = client, context
        self.closed, self.ready = Event(), {}
        self.error = None
        self.socket = None

    def __enter__(self):
        url = urlsplit(self.client.url)
        endpoint = urlunsplit(('wss' if url.scheme == 'https' else 'ws', url.netloc,
                              url.path.rstrip('/') + '/subscriptions', '', ''))
        cookie = '; '.join(f'{c.name}={c.value}' for c in self.client.session.cookies)
        self.socket = websocket.create_connection(endpoint, subprotocols=['graphql-ws'],
            origin=self.client.url, cookie=cookie or None, timeout=10)
        try:
            self.socket.send(json.dumps({'type': 'connection_init'}))
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                message = json.loads(self.socket.recv())
                if message.get('type') == 'connection_ack':
                    break
                if message.get('type') != 'ka':
                    raise ValueError('SysON rejected the editing subscription')
            else:
                raise ValueError('SysON did not acknowledge the editing subscription')
            self.socket.settimeout(1)
            self.thread = Thread(target=self.receive, daemon=True)
            self.thread.start()
            self.subscribe('editingContextEvent', 'EditingContextEventInput', {})
            return self
        except Exception:
            self.close()
            raise

    def receive(self):
        while not self.closed.is_set():
            try:
                message = json.loads(self.socket.recv())
                payload = message.get('payload') or {}
                values = (payload.get('data') or {}).values()
                if message.get('type') in ('error', 'connection_error') or payload.get('errors'):
                    raise ValueError('SysON subscription failed: ' + json.dumps(payload))
                if any(v and v.get('__typename') == 'ErrorPayload' for v in values):
                    raise ValueError('SysON subscription rejected its editing context or diagram')
                if message.get('id') in self.ready:
                    event, needs_payload = self.ready[message['id']]
                    if message.get('type') == 'complete':
                        raise ValueError('SysON closed an active editing subscription')
                    if message.get('type') == 'data' and (payload.get('data') or not needs_payload):
                        event.set()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as error:
                if not self.closed.is_set():
                    self.error = error
                    for event, _ in self.ready.values():
                        event.set()
                return

    def check(self):
        if self.error:
            raise ValueError('SysON live editing session failed: ' + str(self.error)) from self.error

    def subscribe(self, field, input_type, extra):
        identity, event = str(uuid.uuid4()), Event()
        self.ready[identity] = event, bool(extra)
        query = f'subscription($input:{input_type}!){{{field}(input:$input){{__typename}}}}'
        self.socket.send(json.dumps({'type':'start', 'id':identity, 'payload':{'query':query,
            'variables':{'input':{'id':identity, 'editingContextId':self.context, **extra}}}}))
        # EditingContextEvent emits only on a later rename; it has no initial event in 2026.11.
        # DiagramEvent does emit an initial refreshed representation and is our readiness barrier.
        if not extra:
            self.check()
            return
        if not event.wait(30):
            raise ValueError('SysON did not initialize the ' + field + ' subscription')
        self.check()

    def diagram(self, identity):
        self.subscribe('diagramEvent', 'DiagramEventInput', {'diagramId':identity})

    def close(self):
        self.closed.set()
        if self.socket:
            self.socket.close()
        if hasattr(self, 'thread'):
            self.thread.join(timeout=3)

    def __exit__(self, kind, value, traceback):
        self.close()
        if kind is None:
            self.check()
