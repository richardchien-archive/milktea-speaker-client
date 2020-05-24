import io
import wave
from collections import deque

import numpy as np
import pyaudio
import pydub
from scipy import fftpack

CHUNK = 4096  # 每次读取的数据块大小
FORMAT = pyaudio.paInt16
CHANNELS = 1
INPUT_RATE = 44100  # 输入采样率
OUTPUT_RATE = 16000  # 输出采样率


def calc_intensity(data: bytes) -> float:
    rt_data = np.frombuffer(data, np.dtype('<i2'))
    fft_temp_data = fftpack.fft(rt_data, rt_data.size, overwrite_x=True)
    return np.average(np.sqrt(
        np.abs(fft_temp_data)[0:fft_temp_data.size // 2 + 1]))


def test_silence_intensity(num_samples: int = 50):
    """
    测试麦克风在无声时的平均频谱密度, 以便确定适当的阈值.
    """
    print('Getting intensity values from microphone...')
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=INPUT_RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    values = []
    for _ in range(num_samples):
        data = stream.read(CHUNK)
        intensity = calc_intensity(data)
        print(intensity)
        values.append(intensity)
    values = sorted(values, reverse=True)
    avg_int = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
    print(f'Average audio intensity is {avg_int}')
    stream.close()
    audio.terminate()


def listen_for_speech(silence_limit_sec: float = 1.0,
                      prev_audio_sec: float = 0.5,
                      intensity_threshold: float = 70.0) -> bytes:
    """
    监听麦克风, 一旦有语音, 就开始录音, 直到语音结束.

    TODO: 最长 5 秒 silence, 15 秒人声

    Returns:
        Wav 文件二进制数据.
    """
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=INPUT_RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

    print('Listening...')
    recorded = []
    read_count_per_sec = INPUT_RATE // CHUNK
    audio_window = deque(maxlen=int(silence_limit_sec * read_count_per_sec))
    prev_audio = deque(maxlen=int(prev_audio_sec * read_count_per_sec))
    started = False
    while True:
        data = stream.read(CHUNK)
        audio_window.append(calc_intensity(data))
        # print(audio_window[-1])
        if any([x > intensity_threshold for x in audio_window]):
            # 当前窗口内有声音, 应开始或继续录音
            if not started:
                print('Starting record...')
                started = True
            recorded.append(data)
        elif started:
            # 当前窗口内无声音, 且此前已开始录音, 应停止录音 (无声了 SILENCE_LIMIT_SEC 秒)
            print('Finished')
            break
        else:
            # 当前窗口内无声音, 且还没开始录音, 则暂存 (最多暂存 PREV_AUDIO_SEC 秒)
            prev_audio.append(data)

    print('Done recording')
    wav_file_data = bytes_to_wav(b''.join(list(prev_audio) + recorded), audio)
    stream.close()
    audio.terminate()
    return wav_file_data


def bytes_to_wav(data: bytes, audio: pyaudio.PyAudio) -> bytes:
    """
    将原始字节序列转换为 wav 文件数据.
    """
    wav_file = io.BytesIO()
    wf = wave.open(wav_file, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(INPUT_RATE)
    wf.writeframes(data)
    wf.close()

    if INPUT_RATE != OUTPUT_RATE:
        wav_file = io.BytesIO(wav_file.getvalue())
        seg = pydub.AudioSegment.from_file(wav_file)
        seg = seg.set_frame_rate(OUTPUT_RATE)
        wav_file = io.BytesIO()
        seg.export(wav_file, format='wav')

    return wav_file.getvalue()


if __name__ == '__main__':
    import time

    test_silence_intensity()
    # while True:
    #     data = listen_for_speech()
    #
    #     filename = f'output_{str(int(time.time()))}'
    #     with open(f'{filename}.wav', 'wb') as f:
    #         f.write(data)
