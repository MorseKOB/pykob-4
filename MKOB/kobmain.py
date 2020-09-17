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
kobmain.py

Handle the flow of Morse code throughout the program.
"""

import time
from datetime import datetime

from pykob import kob, morse, internet, config, recorder, log
import kobconfig as kc
import kobactions as ka
import kobstationlist
import kobkeyboard

NNBSP = "\u202f"  # narrow no-break space

mySender = None
myReader = None
myRecorder = None
myInternet = None
connected = False

local_loop_active = False  # True if sending on key or keyboard
internet_active = False  # True if a remote station is sending

latch_code = (-0x7fff, +1)  # code sequence to force latching
unlatch_code = (-0x7fff, +2)  # code sequence to unlatch

sender_ID = ""

def set_local_loop_active(state):
    """set local_loop_active state and update Circuit Closer checkbox"""
    global local_loop_active
    local_loop_active = state
    ka.kw.varCircuitCloser.set(1 if not local_loop_active else 0)

def from_key(code):
    """handle inputs received from the external key"""
    global internet_active
    if not internet_active:
        myKOB.setSounder(True)
        update_sender(kc.config.station)
        myReader.decode(code)
        if myRecorder:
            myRecorder.record(code, kob.CodeSource.local)
    if connected and kc.Remote:
        myInternet.write(code)
    if len(code) > 0 and code[-1] == +1:
        set_local_loop_active(False)
        myReader.flush()  # ZZZ is this necessary/desirable?
    else:
        set_local_loop_active(True)

def from_keyboard(code):
    """handle inputs received from the keyboard sender"""
    # ZZZ combine common code with `from_key()`
    global internet_active
    if not internet_active:
        if kc.Local:
            myKOB.sounder(code)
        update_sender(kc.config.station)
        myReader.decode(code)
        if myRecorder:
            myRecorder.record(code, kob.CodeSource.local)
    if connected and kc.Remote:
        myInternet.write(code)
    if len(code) > 0 and code[-1] == +1:
        set_local_loop_active(False)
        myReader.flush()  # ZZZ is this necessary/desirable?
    else:
        set_local_loop_active(True)

def from_internet(code):
    """handle inputs received from the internet"""
    global local_loop_active, internet_active
    if connected:
        myKOB.sounder(code)
        myReader.decode(code)
        if myRecorder:
            myRecorder.record(code, kob.CodeSource.wire)
        if len(code) > 0 and code[-1] == +1:
            internet_active = False
            myReader.flush()  # ZZZ is this necessary/desirable?
        else:
            internet_active = True

def from_circuit_closer(state):
    """handle change of Circuit Closer state"""
    global local_loop_active, internet_active
    code = latch_code if state == 1 else unlatch_code
    if not internet_active:
        if kc.Local:
            update_sender(kc.config.station)
            myKOB.sounder(code)
            myReader.decode(code)
        if myRecorder:
            myRecorder.record(code, kob.CodeSource.local)
    if connected and kc.Remote:
        myInternet.write(code)
    if len(code) > 0 and code[-1] == +1:
        set_local_loop_active(False)
        myReader.flush()  # ZZZ is this necessary/desirable?
    else:
        set_local_loop_active(True)
        
def toggle_connect():
    """connect or disconnect when user clicks on the Connect button"""
    global local_loop_active, internet_active
    global connected
    connected = not connected
    if connected:
        kobstationlist.clear_station_list()
        myInternet.connect(kc.WireNo)
    else:
        myInternet.disconnect()
        myReader.flush()
        time.sleep(1.0)  # wait for any buffered code to complete
        connected = False  # just to make sure
        if not local_loop_active:
            myKOB.sounder(latch_code)
            myReader.decode(latch_code)
            myReader.flush()
        kobstationlist.clear_station_list()
    internet_active = False

def change_wire():
    global local_loop_active, internet_active
    global connected
    if connected:
        connected = False
        myReader.flush()
        time.sleep(1.0)  # wait for any buffered code to complete
        if internet_active:
            internet_active = False
            if not local_loop_active:
                myKOB.sounder(latch_code)
                myReader.decode(latch_code)
                myReader.flush()
        myInternet.connect(kc.WireNo)
        connected = True
    if myRecorder:
        myRecorder.wire = kc.WireNo
    internet_active = False
    
# callback functions

def update_sender(id):
    """display station ID in reader window when there's a new sender"""
    global sender_ID, myReader
    if id != sender_ID:  # new sender
        sender_ID = id
        myReader.flush()
        ka.codereader_append("\n\n<{}>".format(sender_ID))
        kobstationlist.new_sender(sender_ID)
        myReader = morse.Reader(
                wpm=kc.WPM, codeType=kc.CodeType,
                callback=readerCallback)  # reset to nominal code speed
        if myRecorder:
            myRecorder.station_id = sender_ID

def readerCallback(char, spacing):
    """display characters returned from the decoder"""
    if kc.CodeType == config.CodeType.american:
        sp = (spacing - 0.25) / 1.25  # adjust for American Morse spacing
    else:
        sp = spacing
    if sp > 100:
        txt = "" if char == "~" or char == "+" else " * "
    elif sp > 10:
        txt = "  —  "
    elif sp < -0.2:
        txt = ""
    elif sp < 0.2:
        txt = NNBSP
    elif sp < 0.5:
        txt = 2 * NNBSP
    elif sp < 0.8:
        txt = NNBSP + " "
    else:
        n = int(sp - 0.8) + 2
        txt = n * " "
    txt += char
    ka.codereader_append(txt)
    if char == "=":
        ka.codereader_append("\n")

def reset_wire_state():
    """log the current internet state and regain control of the wire"""
    global internet_active
    print(
            "Circuit Closer {}, internet_active was {}".format(
            local_loop_active, internet_active))
    internet_active = False

# initialization

myKOB = kob.KOB(port=kc.config.serial_port, audio=kc.config.sound, callback=from_key)
myInternet = internet.Internet(kc.config.station, callback=from_internet)
myInternet.monitor_IDs(kobstationlist.refresh_stations)
myInternet.monitor_sender(update_sender)
# ZZZ temp always enable recorder - goal is to provide menu option
ts = recorder.getTimestamp()
dt = datetime.fromtimestamp(ts / 1000.0)
print(dt.year, dt.month, dt.day, '-', dt.hour, dt.min, dt.second)
dateTimeStr = str("{:04}{:02}{:02}-{:02}{:02}").format(dt.year, dt.month, dt.day, dt.hour, dt.minute)

targetFileName = "Session-" + dateTimeStr + ".json"
log.info("Record to '{}'".format(targetFileName))
myRecorder = recorder.Recorder(targetFileName, None, station_id=sender_ID, wire=kc.WireNo)
kobkeyboard.init()
