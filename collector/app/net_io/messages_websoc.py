import asyncio
import json
import ssl

import websockets
from websockets.legacy.server import WebSocketServerProtocol

from configs.config import USERS, WS_PORT_MSG, WS_PING_TIMEOUT, WS_PING_INTERVAL, WS_CLOSE_TIMEOUT

WS_PORT = WS_PORT_MSG

PING_TIMEOUT = WS_PING_TIMEOUT
PING_INTERVAL = WS_PING_INTERVAL
CLOSE_TIMEOUT = WS_CLOSE_TIMEOUT

TAG_SYSADMIN = USERS[0]
TAG_DEPTADMIN = USERS[1]
TAG_RECEPTION = USERS[2]


class Message:
    """
        Object that represent a message to send to users. It will be sent after convert it in
        JSON format, by :meth:`jsonify` method.

        :param head: head-text for the message.
        :param msg: the body of the message.
        :param kind: the kind of message [success | info | warning | danger]. Defaults to `info`.
        :param timeout: show-time in seconds.
    """
    kinds = ('success', 'info', 'warning', 'danger')

    def __init__(self, head, msg, kind='info', timeout=3):
        self.check_msg_kind(kind)
        self.body = {
            'head': head,
            'msg': msg,
            'kind': kind,
            'timeout': timeout*1000
        }

    def check_msg_kind(self, kind):
        if kind not in self.kinds:
            raise Exception(f'Message kind "{kind}" NOT ALLOWED')

    def jsonify(self):
        return json.dumps(self.body)


class MSGManagerThreadBody:
    """
    Wrapper-Class that implement WebSocketServer interactions.
    """
    def __init__(self, cert_file, key_file):
        """
        Setup SecureWebSocket parameters
        :param cert_file:
        :param key_file:
        """
        self.process = True

        self.ssl_cert = cert_file
        self.ssl_key = key_file

        # Dictionary structure that contain all Registered WSS, grouped by user-kind
        self.connections = {
            TAG_RECEPTION: set(),
            TAG_DEPTADMIN: set(),
            TAG_SYSADMIN: set()
        }

    def send_message_to(self, dest_tag, head, msg, kind='info', timeout=3):
        """
        Build and send a message to dest_tag WSS
            :param dest_tag: TAG_SYSADMIN, TAG_DAPTADMIN, TAG_RECEPTION
            :param head: head-text for the message.
            :param msg: the body of the message.
            :param kind: the kind of message [success | info | warning | danger]. Defaults to `info`.
            :param timeout: show-time in seconds.
            """
        msg_to_send = Message(head, msg, kind, timeout)
        self.__send_1_message__(dest_tag, msg_to_send)

    def __send_1_message__(self, dest_tag, msg_obj: Message):
        """
        Send a message to desired WSS
        :param dest_tag: username-tag
        :param msg_obj:
        :return:
        """
        assert dest_tag in self.connections.keys()
        websockets.broadcast(self.connections[dest_tag], msg_obj.jsonify())

    def broadcast_message(self, head, msg, kind='info', timeout=3):
        """
        Build and Send a message to all user's Tags
        :param head: Msg title
        :param msg: Msg body
        :param kind:
        :param timeout: GUI show-time in seconds.
        :return:
        """
        msg_to_send = Message(head, msg, kind, timeout)
        self.__broadcast_message__(msg_to_send)

    def __broadcast_message__(self, msg_obj: Message):
        for s in self.connections.values():
            websockets.broadcast(s, msg_obj.jsonify())

    def __call__(self):
        """
        Setup a Secure WebSocket and define async registration function to WebSocketServer
        :return:
        """

        evt_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(evt_loop)

        async def register_ws(ws):
            ws: WebSocketServerProtocol
            try:
                tag_ws = await ws.recv()
                assert tag_ws in self.connections.keys()
                self.connections[tag_ws].add(ws)
            except Exception as e:
                await ws.close(reason=str(e))
                return
            try:
                await ws.wait_closed()
            finally:
                self.connections[tag_ws].remove(ws)

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cert_pem = self.ssl_cert
        key_pem = self.ssl_key

        ssl_context.load_cert_chain(certfile=cert_pem, keyfile=key_pem)

        start_server = websockets.serve(ws_handler=register_ws,
                                        host="0.0.0.0",
                                        port=WS_PORT,
                                        ssl=ssl_context,
                                        ping_timeout=PING_TIMEOUT,
                                        ping_interval=PING_INTERVAL,
                                        close_timeout=CLOSE_TIMEOUT
                                        )

        asyncio.get_event_loop().run_until_complete(start_server)
        # print("server Ready and RUN (Updater)")
        asyncio.get_event_loop().run_forever()
