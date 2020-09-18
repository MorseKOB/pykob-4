#!/usr/bin/env python3
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
syscheck.py

Displays version numbers of Python-related software and the names of
available serial ports.
"""

import sys
print('Python ' + sys.version)

try:
    import pykob
    print('PyKOB ' + pykob.VERSION)
except:
    print('PyKOB not installed')

try:
    import serial
    print('pySerial ' + serial.VERSION)
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        print(' Port: {} {}'.format(p.device, p.description))
except:
    print('pySerial not installed')

try:
    import sounddevice as sd
    print("python-sounddevice ('sounddevice') " + sd.__version__)
    pav = sd.get_portaudio_version()
    print('{} {}'.format(pav[1], pav[0]))
except Exception as ex:
    print("python-sounddevice ('sounddevice') or PortAudio not installed")

try:
    import soundfile as sf
    print('soundfile ' + sf.__version__)
    print('lib soundfile ' + sf.__libsndfile_version__)
except:
    print('soundfile not installed')
