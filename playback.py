import io
import wave
from typing import Any

import pyaudio
import pydub

CHUNK = 1024
OUTPUT_RATE = 44100


def play_wav_file(file: Any):
    seg = pydub.AudioSegment.from_file(file)
    seg = seg.set_frame_rate(OUTPUT_RATE)
    wav_file = io.BytesIO()
    seg.export(wav_file, format='wav')

    wav_file = io.BytesIO(wav_file.getvalue())
    wf = wave.open(wav_file, 'rb')

    # create an audio object
    p = pyaudio.PyAudio()

    # open stream based on the wave object which has been input.
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    # read data (based on the chunk size)
    data = wf.readframes(CHUNK)

    # play stream (looping from beginning of file to the end)
    while data:
        # writing to the stream is what *actually* plays the sound.
        stream.write(data)
        data = wf.readframes(CHUNK)

    # cleanup stuff.
    stream.close()
    p.terminate()


if __name__ == '__main__':
    import sys

    play_wav_file(sys.argv[1])
