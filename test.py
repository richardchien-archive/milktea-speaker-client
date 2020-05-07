import asyncio
import json
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor

import websockets
from aioconsole import aprint

from listener import listen_for_speech

SELF_ID = 'hello123'


async def loop_receive_action(websocket: websockets.WebSocketClientProtocol):
    while True:
        msg = await websocket.recv()
        payload = json.loads(msg)
        await aprint(payload)
        await websocket.send(json.dumps({
            'status': 'ok',
            'data': None,
            'echo': payload.get('echo')
        }))


_message_id = 1


def next_message_id():
    global _message_id
    ret = _message_id
    _message_id += 1
    return ret


async def loop_listen_for_audio_message(
        websocket: websockets.WebSocketClientProtocol):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(1)
    while True:
        wav_file_data = await loop.run_in_executor(executor, listen_for_speech)
        event = {
            'type': 'message',
            'detail_type': 'private',
            'self_id': SELF_ID,
            'message': {
                'type': 'record',
                'data': {
                    'base64': b64encode(wav_file_data).decode()
                }
            },
            'message_id': next_message_id(),
        }
        await websocket.send(json.dumps(event))


async def main():
    uri = "ws://127.0.0.1:8080/ws/"
    async with websockets.connect(uri, extra_headers={
        'X-Self-ID': SELF_ID,
    }) as websocket:
        loop = asyncio.get_event_loop()
        loop.create_task(loop_receive_action(websocket))
        await loop_listen_for_audio_message(websocket)
        # while True:
        #     message = await ainput('>>> ')
        #     event = {
        #         'type': 'message',
        #         'detail_type': 'private',
        #         'self_id': SELF_ID,
        #         'message': message,
        #         'message_id': next_message_id(),
        #     }
        #     await websocket.send(json.dumps(event))


asyncio.get_event_loop().run_until_complete(main())
