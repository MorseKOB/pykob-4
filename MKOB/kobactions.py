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
kobactions.py

Handle actions for controls on main MKOB window
"""

import tkinter as tk
import tkinter.messagebox as mb
import time
from pykob import config, kob, internet, morse
import kobconfig as kc
import kobmain as km
import kobstationlist as ks

import pykob  # for version number
print("PyKOB " + pykob.VERSION)

kw = None  # initialized by KOBWindow

# File menu

def doFileNew():
    kw.txtKeyboard.delete('1.0', tk.END)

def doFileOpen():
## TODO: newFile()
    kw.txtKeyboard.insert(tk.END, "~  Now is the time for all good men to come to the aid of their country.  +")
    kw.txtKeyboard.mark_set('mark', '0.0')
    kw.txtKeyboard.mark_gravity('mark', tk.LEFT)
    kw.txtKeyboard.tag_config('highlight', underline=1)
    kw.txtKeyboard.tag_add('highlight', 'mark')

def doFileExit():
    kw.root.destroy()
    kw.root.quit()

# Help menu

def doHelpAbout():
    mb.showinfo(title="About", message="MorseKOB " + kw.VERSION)

# actions for control events

def doOfficeID(event=None):
    kc.OfficeID = kw.varOfficeID.get()
    config.set_station(kc.OfficeID)
    config.save_config()
    km.myInternet.set_officeID(kc.OfficeID)

def doWPM(event=None):
    kc.WPM = int(kw.spnWPM.get())
    config.set_text_speed(kw.spnWPM.get())
    config.save_config()
    km.mySender = morse.Sender(wpm=kc.WPM, cwpm=kc.CWPM,
            codeType=kc.CodeType, spacing=kc.Spacing)
    km.myReader = morse.Reader(wpm=kc.WPM, codeType=kc.CodeType,
            callback=km.readerCallback)

def doWireNo(event=None):
    kc.WireNo = int(kw.spnWireNo.get())
    config.set_wire(kw.spnWireNo.get())
    config.save_config()
    if km.connected:
        km.change_wire()

def doConnect():
    km.toggle_connect()
    color = 'red' if km.connected else 'white'
    kw.cvsConnect.create_rectangle(0, 0, 20, 20, fill=color)

def codereader_append(s):
    """append a string to the code reader window"""
    kw.txtReader.insert('end', s)
    kw.txtReader.yview_moveto(1)

def escape(event):
    """regain control of the wire"""
    codereader_append("\n<Reset>")
    km.reset_wire_state()
