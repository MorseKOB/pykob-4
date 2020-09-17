"""
MIT License

Copyright (c) 2020 PyKOB - MorseKOB in Python

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
audio module

Provides audio for simulated sounder.
"""

from pathlib import Path
from pykob import log

try:
    import sounddevice as sd
    import soundfile as sf
    ok = True
except:
    log.err("SoundDevice and/or SoundFile not installed, or couldn't create audio output stream.")
    ok = False


clickClackSound = [0, 0]
soundData = [[],[]]
sound = 0

if ok:
    # Get the 'Resource' folder
    root_folder = Path(__file__).parent
    resource_folder = root_folder / "resources"
    # Audio files
    audio_files = ['clack48.wav', 'click48.wav']

    for i in range(len(audio_files)):
        fn = resource_folder / audio_files[i]
        log.info("Load audio file: {}".format(fn))
        # Extract data and sampling rate from file
        with sf.SoundFile(fn) as f:
            data = f.buffer_read(frames=-1, dtype='int32')
            soundData[i] = [data, f.channels]

def play(snd):
    global soundData
    soundInfo = soundData[snd]
    audioData = soundInfo[0]
    channels = soundInfo[1]
    audioOutputStream = sd.RawOutputStream(latency='low', blocksize=0, channels=channels, dtype='int32')
    with audioOutputStream:
        audioOutputStream.write(audioData)

"""
Test code
"""
if __name__ == "__main__":
    # Self-test
    import time
    #  Play 'click' and 'clack'
    play(0)
    time.sleep(0.3)
    play(1)
    time.sleep(0.3)
    play(0)
    time.sleep(0.3)
    play(1)
