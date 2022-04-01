import asyncio
import pickle
import queue
import ssl
import time
from logging import log, ERROR

import websockets as websockets
from websockets.exceptions import ConnectionClosedError
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.server import WebSocketServerProtocol

from utils.frames_dict import FramesDict

from configs.config import WS_PORT_VIDEO, WS_PING_TIMEOUT, WS_PING_INTERVAL, WS_CLOSE_TIMEOUT, video_token

WS_PORT = WS_PORT_VIDEO

PING_TIMEOUT = WS_PING_TIMEOUT
PING_INTERVAL = WS_PING_INTERVAL
CLOSE_TIMEOUT = WS_CLOSE_TIMEOUT


class VideoGatherThreadBody:
    """
    Thread-Body that setup and receive debug-frames stream from MUs
    """
    def __init__(self, f_dict: FramesDict, cert_file, key_file):
        """
        :param f_dict: FrameDictionary object, to keep in memory the last frame sent form each MU
        :param cert_file: public_cert.pem
        :param key_file: private_key.pem
        """
        self.frames_dict = f_dict
        self.process = True
        self.ssl_cert = cert_file
        self.ssl_key = key_file

    def __call__(self):
        """
        Setup the Secure WebSocket, defining the callback function that receive frames from a MU
        :return:
        """
        evt_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(evt_loop)

        async def get_frames(ws):
            ws: WebSocketServerProtocol
            # print('Connection Opened')
            listen = True
            sent = None

            send_ack = 0

            msg = await ws.recv()
            if msg != video_token:
                await ws.close(code=404)

            while listen:
                try:
                    # if sent is not None and sent.cr_running:
                    #     print('\n... sent.cr_running ...\n')
                    if sent is not None:
                        await sent
                        sent = None
                    msg = await ws.recv()
                    (dev_id, img) = pickle.loads(msg)
                    self.frames_dict.add_frame(dev_id, img)

                    send_ack = (send_ack + 1) % 100
                    if send_ack == 0:
                        sent = ws.send('OK')
                except ConnectionClosedError as e:
                    log(ERROR, f'[WS-Handler]: {e}')
                    listen = False
            # print('')
            # print('Connection Closed')

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cert_pem = self.ssl_cert
        key_pem = self.ssl_key

        ssl_context.load_cert_chain(certfile=cert_pem, keyfile=key_pem)

        start_server = websockets.serve(ws_handler=get_frames,
                                        host="0.0.0.0",
                                        port=WS_PORT,
                                        ssl=ssl_context,
                                        ping_timeout=PING_TIMEOUT,
                                        ping_interval=PING_INTERVAL,
                                        close_timeout=CLOSE_TIMEOUT
                                        )

        asyncio.get_event_loop().run_until_complete(start_server)
        # print("server Ready and RUN")
        asyncio.get_event_loop().run_forever()


class VideoStreamerThreadBody:
    """
    Thread body to use to interact with Frames-gather Server-Side WSS
    """
    def __init__(self, serv_addr='localhost', host_id='host_name', ca_file='ca_cert.pem'):
        """
        :param serv_addr:
        :param host_id: Hostname used to be identified from Server-Side
        :param ca_file: Full-chain certificate to believe in
        """
        self.q_frames = queue.Queue(maxsize=30)
        self.uri = f"wss://{serv_addr}:{WS_PORT}"
        self.ca_file = ca_file
        self.process = True
        self.my_name = host_id

    def __call__(self):
        """
        Setup WSS client-side and define the client-side protocol

        :return:
        """
        async def send_frames():
            uri = self.uri
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ca_cert_pem = self.ca_file

            print(f'FILE = {ca_cert_pem}')
            ssl_context.load_verify_locations(cafile=ca_cert_pem)
            # ssl_context.load_cert_chain(certfile=ca_cert_pem)

            while self.process:
                flooding = True
                try:
                    life_start = time.time()
                    async with websockets.connect(uri,
                                                  ssl=ssl_context,
                                                  ping_timeout=PING_TIMEOUT,
                                                  ping_interval=PING_INTERVAL,
                                                  close_timeout=CLOSE_TIMEOUT
                                                  ) as ws:
                        ws: WebSocketClientProtocol
                        # ws.ping()
                        print('Connection Opened')
                        # ws.connection_lost()
                        ack = None
                        read_ack = 0
                        empty_cnt = 0
                        while flooding and ws.open:
                            try:

                                if ack is not None and not ack.cr_running:
                                    r = await ack
                                    ack = None
                                    if r != 'OK':
                                        raise Exception('Server Connection Lost (in time and space)')

                                if ack is not None and ack.cr_running:
                                    print('RUNNING')

                                if self.q_frames.empty():
                                    # time.sleep(1/10)
                                    empty_cnt += 1
                                    await ws.ping()
                                    await asyncio.sleep(1 / 20)
                                    continue

                                if empty_cnt > 0:
                                    # print(f'Skip count: {empty_cnt}')
                                    empty_cnt = 0

                                read_ack = (read_ack + 1) % 100

                                f = self.q_frames.get_nowait()
                                msg = pickle.dumps((self.my_name, f))
                                # await ping
                                await ws.send(msg)
                                # print("sent msg")

                                if read_ack == 0:
                                    ack = ws.recv()

                            except Exception as e:
                                log(level=ERROR, msg=f'VideoStreamer: {e}')
                                flooding = False
                                await ws.close_connection()
                        print('Connection Closed')

                    life_end = time.time()
                    life_time = int(life_end - life_start)
                    print(f'# Lifetime: {life_time}s')
                except Exception as e:
                    # except ConnectionRefusedError as e:
                    log(ERROR, f'[WS-Sender]: {e}')

        evt_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(evt_loop)

        asyncio.get_event_loop().run_until_complete(send_frames())

