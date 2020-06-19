import asyncio
import io
import json
from base64 import b64encode, b64decode
from concurrent.futures import ThreadPoolExecutor

import websockets
from aioconsole import aprint

from listen import listen_for_speech
from playback import play_wav_file

SELF_ID = 'hello123'

executor = ThreadPoolExecutor(1)


async def receive_action(websocket: websockets.WebSocketClientProtocol):
    loop = asyncio.get_event_loop()

    msg = await websocket.recv()
    payload = json.loads(msg)
    await aprint(payload)

    await websocket.send(json.dumps({
        'status': 'ok',
        'data': None,
        'echo': payload.get('echo')
    }))

    # TODO: 提取 action 处理逻辑
    action = payload['action']
    params = payload['params']
    if action == 'send':
        for seg in params['message']:
            if seg['type'] != 'record':
                continue
            speech_base64 = seg['data'].get('base64')
            if not speech_base64:
                continue
            # TODO: 需要能够放到一半停(可以用一个线程不断播放, 其它线程往里面喂 data frame 即可)
            wav_file_data = b64decode(speech_base64)
            # t = threading.Thread(target=play_wav_file,
            #                      args=(io.BytesIO(wav_file_data),))
            # t.start()
            await loop.run_in_executor(executor, play_wav_file,
                                       io.BytesIO(wav_file_data))
            break

    return params.get('should_continue', False)


async def loop_receive_action(websocket: websockets.WebSocketClientProtocol):
    while True:
        await receive_action(websocket)


_message_id = 1


def next_message_id():
    global _message_id
    ret = _message_id
    _message_id += 1
    return ret


async def listen_for_audio_message(
        websocket: websockets.WebSocketClientProtocol):
    loop = asyncio.get_event_loop()
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


async def loop_listen_for_audio_message(
        websocket: websockets.WebSocketClientProtocol):
    while True:
        await listen_for_audio_message(websocket)


async def main():
    uri = "ws://127.0.0.1:8080/ws/"
    async with websockets.connect(uri, extra_headers={
        'X-Self-ID': SELF_ID,
    }) as websocket:
        should_continue = True
        while should_continue:
            await listen_for_audio_message(websocket)
            should_continue = await receive_action(websocket)

        # await loop_listen_for_audio_message(websocket)
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


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
