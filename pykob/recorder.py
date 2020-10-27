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
Recorder class

Records wire and local station information for analysis and playback.
Plays back recorded information.

The information is recorded in packets in a JSON structure that includes:
1. Timestamp
2. Source (`local`/`wire`)
3. Station ID
4. Wire Number
5. Code type
6. Code Sequence (key timing information)

Though the name of the class is `recorder` it is typical that a 'recorder' can also
play back. For example, a 'tape recorder', a 'video casset recorder (VCR)',
a 'digital video recorder' (DVR), etc. can all play back what they (and compatible
devices) have recorded. This class is no exception. It provides methods to play back
recordings in addition to making recordings.

"""
import json
import queue
import threading
import time
from datetime import datetime, timedelta
from enum import Enum, IntEnum, unique
from pykob import config, kob, log
from threading import Lock, RLock

@unique
class PlaybackState(IntEnum):
    """
    The current state of recording playback.
    """
    idle = 0
    playing = 1
    paused = 2

def get_timestamp() -> int:
    """
    Return the current  millisecond timestamp.

    Return
    ------
    ts : number
        milliseconds since the epoc
    """
    ts = int(time.time() * 1000)
    return ts
    
def date_time_from_ts(ts: int) -> str:
    """
    Return a Date-Time string from a timestamp.

    ts : int
        milliseconds since the epec
    Return
    ------
    dtstr : string
        A string with the date and time
    """
    dateTime = datetime.fromtimestamp(ts / 1000.0)
    dateTimeStr = str(dateTime.ctime()) + ": "
    return dateTimeStr

def hms_from_ts(ts1: int, ts2: int) -> str:
    """
    Return a string with HH:MM:SS from a pair of timestamp values.

    ts1 : int
        Timestamp 1
    ts2 : int
        Timestamp 2
    Return
    ------
    hms : string
        A string in the form HH:MM:SS calculated from the two timestamps.
    """
    duration = abs(ts1 - ts2)
    tdelta = timedelta(milliseconds=duration)
    return str(tdelta)

class Recorder:
    """
    Recorder class provides functionality to record and playback a code stream.
    """

    def __init__(self, target_file_path:str=None, source_file_path:str=None, \
            station_id:str="", wire:int=-1, \
            play_code_callback=None, \
            play_finished_callback=None, \
            play_station_id_callback=None, \
            play_wire_callback=None, \
            play_station_list_callback=None):
        self.__target_file_path = target_file_path
        self.__source_file_path = source_file_path
        self.__station_id = station_id
        self.__wire = wire

        self.__play_code_callback = play_code_callback
        self.__play_finished_callback = play_finished_callback
        self.__play_station_id_callback = play_station_id_callback
        self.__play_station_list_callback = play_station_list_callback
        self.__play_wire_callback = play_wire_callback

        self.__playback_state = PlaybackState.idle

        self.__playback_thread = None
        self.__p_stations_thread = None

        self.__playback_resume_flag = threading.Event()
        self.__playback_stop_flag = threading.Event()

        self.__playback_code = None
        self.__list_data = False
        self.__max_silence = 0
        self.__speed_factor = 100

        # Information about the current playback file
        self.__p_line_no = 0            # Current line number being processed/played
        self.__p_lines = 0              # Number of lines in the file
        self.__p_fts = 0                # First (earliest) timestamp
        self.__p_lts = 0                # Last (latest) timestamp
        self.__p_fpts_index = []        # List of tuples with timestamp, file-position and station-change
        self.__p_stations = set()       # Set of all stations in the recording
        self.__p_fp = None              # File pointer for current playback file while playing
        self.__p_pblts = -1             # Playback last timestamp
        self.__p_fileop_lock = Lock()   # Lock to protect file operation access from play and seek threads

    @property
    def playback_stations(self):
        """
        Set of the stations contained in the recording being played.
        """
        return self.__p_stations

    @property
    def playback_state(self):
        """
        The current PlaybackState.
        """
        return self.__playback_state

    @property
    def source_file_path(self) -> str:
        """
        The path to the source file used to play back a code sequence stored in PyKOB JSON format.
        """
        return self.__source_file_path

    @source_file_path.setter
    def source_file_path(self, path: str):
        """
        Set the source file path.
        """
        self.__source_file_path = path

    @property
    def target_file_path(self) -> str:
        """
        The path to the target file used to record a code sequence in PyKOB JSON format.
        """
        return self.__target_file_path

    @target_file_path.setter
    def target_file_path(self, target_file_path: str):
        """
        Set the target file path to record to.
        """
        self.__target_file_path = target_file_path

    @property
    def station_id(self) -> str:
        """
        The Station ID.
        """
        return self.__station_id

    @station_id.setter
    def station_id(self, station_id: str):
        """
        Set the Station ID.
        """
        if self.__station_id != station_id:
            self.__station_id = station_id
            if self.__play_station_id_callback and not self.playback_state == PlaybackState.idle:
                self.__play_station_id_callback(station_id)

    @property
    def wire(self) -> int:
        """
        The Wire.
        """
        return self.__wire

    @wire.setter
    def wire(self, wire: int):
        """
        Set the Wire.
        """
        if self.__wire != wire:
            self.__wire = wire
            if self.__play_wire_callback and not self.playback_state == PlaybackState.idle:
                self.__play_wire_callback(wire)

    def record(self, code, source):
        """
        Record a code sequence in JSON format with additional context information.
        """
        if self.__playback_state == PlaybackState.idle: # Only record if not playing back a recording
            timestamp = get_timestamp()
            data = {
                "ts":timestamp,
                "w":self.wire,
                "s":self.station_id,
                "o":source,
                "c":code
            }
            with open(self.__target_file_path, "a+") as fp:
                json.dump(data, fp)
                fp.write('\n')

    def playback_move_seconds(self, seconds: int):
        """
        Change the current playback position forward/backward 'seconds' seconds.

        A recording must be playing or this method does nothing.
        """
        # ###
        # This calculates a new file position using the current line number being played 
        # and using the index to find the position to move forward or backward based on 
        # the requested change and the timestamps in the index.
        #
        # The movement will be => than the request based on the timestamps for the lines 
        # in the recording.
        #
        # This is done using the file-operation lock so the playback can't change while 
        # the position is being changed. By using the index, this method doesn't take 
        # long to change the position. Since the playback is going to change anyway, 
        # the pause doesn't really matter.
        # ###
        if seconds == 0:
            return
        with self.__p_fileop_lock: # Lock out any other file access first
            if self.__p_fp:
                current_lineno = self.__p_line_no
                indexlen = len(self.__p_fpts_index)
                if current_lineno > 0 and current_lineno < indexlen - 1:
                    current_ts = self.__p_fpts_index[current_lineno][0]
                    current_pos = self.__p_fpts_index[current_lineno][1]
                    target_ts = current_ts + (seconds * 1000) # Calculate the target timestamp
                    nts = current_ts
                    new_pos = current_pos
                    # Move forward or backward?
                    if seconds > 0:
                        # Forward...
                        for i in range(current_lineno, indexlen - 1):
                            nts = self.__p_fpts_index[i][0]
                            if nts >= target_ts or i == indexlen - 1:
                                # If we move one line and the timestamp is >= target, we are done
                                new_pos = self.__p_fpts_index[i][1] # An index entry is [ts,fpos,station-change]
                                print(" Move forward to line: {} From: {}  Pos: {} From: {}  Timestamp: {} From: {}".format(\
                                    i, current_lineno, new_pos, current_pos, nts, current_ts))
                                self.__p_line_no = i
                                self.__p_fp.seek(new_pos)
                                self.__p_pblts = nts # set last timestamp to the new timestamp so there isn't a delay when played
                                break
                    else:
                        # Backward...
                        for i in range(current_lineno, 0, -1):
                            nts = self.__p_fpts_index[i][0]
                            if nts <= target_ts or i == 0:
                                # If we move one line and the timestamp is <= target, we are done
                                new_pos = self.__p_fpts_index[i][1] # An index entry is [ts,fpos,station-change]
                                print(" Move backward to line: {} From: {}  Pos: {} From: {}  Timestamp: {} From: {}".format(\
                                    i, current_lineno, new_pos, current_pos, nts, current_ts))
                                self.__p_line_no = i
                                self.__p_fp.seek(new_pos)
                                self.__p_pblts = nts # set last timestamp to the new timestamp so there isn't a delay when played
                                break

    def playback_move_to_sender_begin(self):
        """
        Change the current playback position back to the beginning of the 
        current sender.

        A recording must be playing or this method does nothing.
        """
        # ###
        # This calculates a new file position using the current line number being played 
        # and using the index to find the position to move backward to based on 
        # the sender/station change flag in the index.
        #
        # This is done using the file-operation lock so the playback can't change while 
        # the position is being changed. By using the index, this method doesn't take 
        # long to change the position. Since the playback is going to change anyway, 
        # the pause doesn't really matter.
        # ###
        with self.__p_fileop_lock: # Lock out any other file access first
            if self.__p_fp:
                current_lineno = self.__p_line_no
                indexlen = len(self.__p_fpts_index)
                if current_lineno > 0 and current_lineno < indexlen - 1:
                    current_ts = self.__p_fpts_index[current_lineno][0]
                    current_pos = self.__p_fpts_index[current_lineno][1]
                    # Move back through the index checking for a station change
                    for i in range(current_lineno, 0, -1):
                        sc = self.__p_fpts_index[i][2] # An index entry is [ts,fpos,station-change]
                        if sc:
                            # We found a station change. Go back one more line if possible.
                            if i > 0:
                                i -= 1
                            new_pos = self.__p_fpts_index[i][1]
                            nts = self.__p_fpts_index[i][0]
                            print(" Move back to beginning of sender. Line: {} From: {}  Pos: {} From: {}  Timestamp: {} From: {}".format(\
                                i, current_lineno, new_pos, current_pos, nts, current_ts))
                            self.__p_line_no = i
                            self.__p_fp.seek(new_pos)
                            self.__p_pblts = nts # set last timestamp to the new timestamp so there isn't a delay when played
                            break

    def playback_move_to_sender_end(self):
        """
        Change the current playback position to the end of the 
        current sender.

        A recording must be playing or this method does nothing.
        """
        # ###
        # This calculates a new file position using the current line number being played 
        # and using the index to find the position to move forward to based on 
        # the sender/station change flag in the index.
        #
        # This is done using the file-operation lock so the playback can't change while 
        # the position is being changed. By using the index, this method doesn't take 
        # long to change the position. Since the playback is going to change anyway, 
        # the pause doesn't really matter.
        # ###
        with self.__p_fileop_lock: # Lock out any other file access first
            if self.__p_fp:
                current_lineno = self.__p_line_no
                indexlen = len(self.__p_fpts_index)
                if current_lineno > 0 and current_lineno < indexlen - 1:
                    current_ts = self.__p_fpts_index[current_lineno][0]
                    current_pos = self.__p_fpts_index[current_lineno][1]
                    # Move forward through the index checking for a station change
                    for i in range(current_lineno, indexlen-1):
                        sc = self.__p_fpts_index[i][2] # An index entry is [ts,fpos,station-change]
                        if sc:
                            # We found a station change. Go back one line if possible.
                            if i > 0:
                                i -= 1
                            new_pos = self.__p_fpts_index[i][1]
                            nts = self.__p_fpts_index[i][0]
                            print(" Move forward to next sender. Line: {} From: {}  Pos: {} From: {}  Timestamp: {} From: {}".format(\
                                i, current_lineno, new_pos, current_pos, nts, current_ts))
                            self.__p_line_no = i
                            self.__p_fp.seek(new_pos)
                            self.__p_pblts = nts # set last timestamp to the new timestamp so there isn't a delay when played
                            break

    def playback_resume(self):
        """
        Resume a paused playback.

        The `playback_start` method must have been called to set up the necessary state 
        and `playback_pause` must have been called to pause the current playback. Otherwise 
        this method does nothing.
        """
        if self.__playback_state == PlaybackState.paused:
            self.__playback_state = PlaybackState.playing
            self.__playback_resume_flag.set()
    
    def playback_pause(self):
        """
        Pause a currently playing recording.

        A recording must be playing or this method does nothing.
        """
        if self.__playback_state == PlaybackState.playing:
            self.__playback_resume_flag.clear()
            self.__playback_state = PlaybackState.paused

    def playback_pause_resume(self):
        """
        Pause playback if playing, resume playback if paused. 

        This does nothing if there isn't a playback in progress.
        """
        if self.__playback_state == PlaybackState.idle:
            return
        if self.__playback_state == PlaybackState.playing:
            self.playback_pause()
        else:
            self.playback_resume()

    def playback_stop(self):
        """
        Stop playback and clear the playback state
        """
        if self.__playback_thread:
            pt = self.__playback_thread
            self.__playback_thread = None
            self.__playback_stop_flag.set()
            self.__playback_resume_flag.set() # Set resume flag incase playback was paused

    def playback_start(self, list_data=False, max_silence=0, speed_factor=100):
        """
        Play a recording to the configured sounder.
        """
        self.playback_stop()
        self.__playback_resume_flag.clear()
        self.__playback_stop_flag.clear()

        self.__p_fts = -1
        self.__p_lts = 0
        self.__p_stations.clear()
        self.__p_fpts_index = []
        self.__p_line_no = 0
        self.__p_lines = 0
        self.__station_id = None
        self.__wire = None
        #
        # Get information from the current playback recording file.
        with open(self.__source_file_path, "r") as fp:
            self.__p_fpts_index.append((0,0,False)) # Store line 0 as Time=0, Pos=0, Sender-Change=False
            previous_station = None
            # NOTE: Can't iterate over the file lines as it disables `tell()` and `seek()`.
            line = fp.readline()
            while line:
                try:
                    fpos = fp.tell()
                    data = json.loads(line)
                    ts = data['ts']
                    wire = data['w']
                    station = data['s']
                    ts = data['ts']
                    station = data['s']
                    # Store the file position and timestamp in the index to use 
                    # for seeking to a line based on time or line number
                    self.__p_fpts_index.append((ts,fpos,station != previous_station))
                    previous_station = station
                    # Get the first and last timestamps from the recording
                    if self.__p_fts == -1 or ts < self.__p_fts:
                        self.__p_fts = ts # Set the 'first' timestamp
                    if self.__p_lts < ts:
                        self.__p_lts = ts
                    # Update the number of lines
                    self.__p_lines +=1
                    # Generate the station list from the recording
                    self.__p_stations.add(station)
                    # Read the next line
                    line = fp.readline()
                except Exception as ex:
                    log.err("Error processing recording file: '{}' Line: {} Error: {}".format(self.__source_file_path, self.__p_line_no, ex))
                    return
        # Calculate recording file values to aid playback functions
        # Print some values about the recording
        print(" Lines: {}  Start: {}  End: {}  Duration: {}".format(self.__p_lines, date_time_from_ts(self.__p_fts), date_time_from_ts(self.__p_lts), hms_from_ts(self.__p_lts, self.__p_fts)))
        self.__list_data = list_data
        self.__max_silence = max_silence
        self.__speed_factor = speed_factor
        self.__playback_thread = threading.Thread(name='Recorder-Playback-Play', daemon=True, target=self.callbackPlay)
        self.__playback_thread.start()
        if self.__play_station_list_callback:
            self.__p_stations_thread = threading.Thread(name='Recorder-Playback-StationList', daemon=True, target=self.callbackPlayStationList)
            self.__p_stations_thread.start()

    def callbackPlay(self):
        """
        Called by the playback thread `run` to playback recorded code.
        """
        self.__p_line_no = 0
        self.__p_pblts = -1 # Keep the last timestamp

        try:
            if not self.source_file_path:
                return

            self.__playback_state = PlaybackState.playing
            #
            # With the information from the recording, call the station callback (if set)
            print('Stations in recording:')
            for s in self.__p_stations:
                print(' Station: ', s)
                if self.__play_station_list_callback:
                    self.__play_station_list_callback(s)
            with open(self.__source_file_path, "r") as self.__p_fp:
                with self.__p_fileop_lock:
                    # NOTE: Can't iterate over the file lines as it disables `tell()` and `seek()`.
                    line = self.__p_fp.readline()
                    self.__p_line_no += 1
                while line:
                    # Get the file lock and read the contents of the line
                    with self.__p_fileop_lock:
                        while self.__playback_state == PlaybackState.paused:
                            self.__playback_resume_flag.wait() # Wait for playback to be resumed
                            self.__playback_state = PlaybackState.playing
                        if self.__playback_stop_flag.is_set():
                            # Playback stop was requested
                            self.__playback_state = PlaybackState.idle
                            self.__playback_resume_flag.clear()
                            return
                        data = json.loads(line)
                        #
                        code = data['c']        # Code sequence
                        ts = data['ts']         # Timestamp
                        wire = data['w']        # Wire number
                        station = data['s']     # Station ID
                        source = data['o']      # Source/Origin (numeric value from kob.CodeSource)
                        pblts = self.__p_pblts
                        self.__p_pblts = ts
                        # Done with lock

                    try:
                        if pblts < 0:
                            pblts = ts
                        if self.__list_data:
                            print(date_time_from_ts(ts), line, end='')
                        if code == []:  # Ignore empty code packets
                            continue
                        codePause = -code[0] / 1000.0  # delay since end of previous code sequence and beginning of this one
                        # For short pauses (< 2 sec), `KOB.sounder` can handle them more precisely.
                        # However the way `KOB.sounder` handles longer pauses, although it makes sense for
                        # real-time transmissions, is flawed for playback. Better to handle long pauses here.
                        # A pause of 0x3777 ms is a special case indicating a discontinuity and requires special
                        # handling in `KOB.sounder`.
                        #
                        # Also check for station change code sequence. If so, pause for recorded timestamp difference
                        if self.__playback_state == PlaybackState.playing:
                            pause = 0
                            if codePause == 32.767 and len(code) > 1 and code[1] == 2:
                                # Probable sender change. See if it is...
                                if not station == self.station_id:
                                    if self.__list_data:
                                        print("Sender change.")
                                    pause = round((ts - pblts)/1000, 4)
                            elif codePause > 2.0 and codePause < 32.767:
                                # Long pause in sent code
                                pause = round((((ts - pblts)/1000) - 2.0), 4) # Subtract 2 seconds so kob has some to handle
                                code[0] = -2000  # Change pause in code sequence to 2 seconds since the rest is handled
                            if pause > 0:
                                # Long pause or a station/sender change.
                                # For very long delays, sleep a maximum of `max_silence` seconds
                                if self.__max_silence > 0 and pause > self.__max_silence:
                                    if self.__list_data:
                                        print("Realtime pause of {} seconds being reduced to {} seconds".format(pause, self.__max_silence))
                                    pause = self.__max_silence
                                time.sleep(pause)
                        if not self.__speed_factor == 100:
                            sf = 1.0 / (self.__speed_factor / 100.0)
                            for c in code:
                                if c < 0 or c > 2:
                                    c = round(sf * c)
                        self.wire = wire
                        self.station_id = station
                        if self.__play_code_callback:
                            self.__play_code_callback(code)
                    finally:
                        # Read the next line to be ready to continue the processing loop.
                        with self.__p_fileop_lock:
                            line = self.__p_fp.readline()
                            self.__p_line_no += 1
        finally:
            if self.__play_finished_callback:
                self.__play_finished_callback()
            with self.__p_fileop_lock:
                self.__p_fp = None
            print("Playback done.")


    def callbackPlayStationList(self):
        """
        Called by the station list thread run method to update a station list 
        via the registered callback. The station list is refreshed every 5 seconds.
        """
        if not self.__play_station_list_callback:
            return
        while True:
            for stn in self.__p_stations:
                self.__play_station_list_callback(stn)
            stop = self.__playback_stop_flag.wait(5.0) # Wait until 'stop' flag is set or 5 seconds
            if stop:
                return # Stop signalled - return from run method

"""
Test code
"""
if __name__ == "__main__":
    # Self-test
    from pykob import morse

    test_target_filename = "test." + str(get_timestamp()) + ".json"
    myRecorder = Recorder(test_target_filename, test_target_filename, station_id="Test Recorder", wire=-1)
    mySender = morse.Sender(20)

    # 'HI' at 20 wpm as a test
    print("HI")
    codesequence = (-1000, +2, -1000, +60, -60, +60, -60, +60, -60, +60,
            -180, +60, -60, +60, -1000, +1)
    myRecorder.record(codesequence, kob.CodeSource.local)
    # Append more text to the same file
    for c in "This is a test":
        codesequence = mySender.encode(c, True)
        myRecorder.record(codesequence, kob.CodeSource.local)
    print()
    # Play the file
    myKOB = kob.KOB(port=None, audio=True)
    myRecorder.playback(myKOB)

