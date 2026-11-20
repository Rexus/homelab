"""Native subscriptions must initialize, surface errors and close on all publication paths."""
import json
from pathlib import Path
from queue import Queue, Empty
from types import SimpleNamespace
import unittest
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/architecture'))
from syson_session import EditingSession
import websocket


class Socket:
    def __init__(self, rejected=False):
        self.messages, self.sent, self.closed, self.rejected = Queue(), [], False, rejected

    def settimeout(self, value):
        pass

    def send(self, text):
        message=json.loads(text)
        self.sent.append(message)
        if message['type']=='connection_init':
            self.messages.put({'type':'connection_ack'})
        elif message['type']=='start':
            identity=message['id']
            if self.rejected:
                self.messages.put({'type':'data','id':identity,'payload':{'errors':[{'message':'rejected'}]}})
            else:
                self.messages.put({'type':'data','id':identity})
                if 'diagramId' in message['payload']['variables']['input']:
                    self.messages.put({'type':'data','id':identity,'payload':{
                        'data':{'diagramEvent':{'__typename':'DiagramRefreshedEventPayload'}}}})

    def recv(self):
        try:
            return json.dumps(self.messages.get(timeout=.05))
        except Empty:
            raise websocket.WebSocketTimeoutException()

    def close(self):
        self.closed=True


class NativeSession(unittest.TestCase):
    def client(self):
        return SimpleNamespace(url='http://localhost:8080',session=SimpleNamespace(cookies=[]))

    def test_subscription_lifetime_covers_both_representations(self):
        socket=Socket()
        with patch('syson_session.websocket.create_connection',return_value=socket) as connect:
            with EditingSession(self.client(),'context') as live:
                live.diagram('intake')
                live.diagram('overall')
                self.assertFalse(socket.closed)
                self.assertEqual(len(live.ready),3)
                live.check()
        self.assertTrue(socket.closed)
        self.assertEqual(connect.call_args.args[0],'ws://localhost:8080/subscriptions')
        self.assertEqual(connect.call_args.kwargs['subprotocols'],['graphql-ws'])

    def test_subscription_error_cannot_be_reported_as_initialized(self):
        socket=Socket(rejected=True)
        with patch('syson_session.websocket.create_connection',return_value=socket):
            with self.assertRaisesRegex(ValueError,'subscription failed'):
                with EditingSession(self.client(),'context') as live:
                    live.diagram('intake')
                    self.fail('Rejected subscription initialized its diagram')
        self.assertTrue(socket.closed)

    def test_caller_error_closes_subscription(self):
        socket=Socket()
        with patch('syson_session.websocket.create_connection',return_value=socket):
            with self.assertRaisesRegex(ValueError,'publication failed'):
                with EditingSession(self.client(),'context'):
                    raise ValueError('publication failed')
        self.assertTrue(socket.closed)
