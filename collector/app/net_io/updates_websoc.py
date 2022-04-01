import asyncio
import json
import ssl

import websockets

from configs.config import WS_PORT_UPDATES, WS_PING_TIMEOUT, WS_PING_INTERVAL, WS_CLOSE_TIMEOUT

WS_PORT = WS_PORT_UPDATES

PING_TIMEOUT = WS_PING_TIMEOUT
PING_INTERVAL = WS_PING_INTERVAL
CLOSE_TIMEOUT = WS_CLOSE_TIMEOUT


class UpdateManagerThreadBody:
    """
    Implementation of thread that take care of broadcast updates on Counts Estimations
    (Persons: Entered/Exited/Estimated-Inside)
    """
    def __init__(self, init_updates, cert_file, key_file):
        """
        :param init_updates: init value to be broadcasted
        :param cert_file: public_cert.pem
        :param key_file: private_key.pem
        """
        self.init_updates = init_updates
        self.process = True
        self.ssl_cert = cert_file
        self.ssl_key = key_file
        self.connections = set()
        self.some_error = False

    def broadcast_update(self, data: dict):
        """
        Send to all registered client the current Counts estimations.
        Furthermore, add a new field to `data` dict, that represent if there is some error in PeopleCounts estimation
        :param data: {in: x, out: y, tot: z}
        :return:
        """
        data['error'] = self.some_error
        data_j = json.dumps(data)
        websockets.broadcast(self.connections, data_j)
        self.init_updates = data_j

    def __call__(self):
        """
        Setup a Secure WebSocket and define async registration-function to WebSocketServer
        :return:
        """
        evt_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(evt_loop)

        async def register_ws_upd(ws):
            # ws: WebSocketServerProtocol
            # print('Connection Opened (Updates)')
            self.connections.add(ws)
            try:
                await ws.send(self.init_updates)
                await ws.wait_closed()
            finally:
                self.connections.remove(ws)

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cert_pem = self.ssl_cert
        key_pem = self.ssl_key

        ssl_context.load_cert_chain(certfile=cert_pem, keyfile=key_pem)

        start_server = websockets.serve(ws_handler=register_ws_upd,
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
