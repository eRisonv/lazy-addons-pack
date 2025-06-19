import json
import os
import configparser
from typing import List
import bpy
from datetime import date as d, datetime


def write_json(data, file):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def read_json(file):
    try:
        with open(file) as f:
            data = json.load(f)
            return data
    except:
        print(f"Error reading {file}")
        return None
    

def read_config(file):
    config = configparser.ConfigParser()
    try:
        config.read(file)
    except:
        print(f"Error reading {file}")
    return config

def write_config(config, file):
    with open(file, 'w') as configfile:
        config.write(configfile)


def get_addon_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_template(filename):
    return os.path.join(get_addon_dir(), 'templates', filename)


# default
def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def open_folder(path):
    dir = path
    if os.path.isfile(path):
        dir = os.path.dirname(path)

    os.startfile(dir) # open folder


def get_properties(context):
    return context.scene.time_tracker_props


def get_blender_path(path):
    abs_path = bpy.path.abspath(path)
    if not os.path.exists(abs_path):
        return None
    return abs_path


import datetime
def get_time_pretty(seconds: int) -> str:
    delta = datetime.timedelta(seconds=seconds)
    return f"{delta}"


"""
returns data_dir path
"""
def get_data_dir():
    # Compatible with Blender 4.0.2
    return bpy.utils.user_resource('DATAFILES', path='time_tracker_data', create=True)


from .properties import TIME_TRACK_FILE
def get_time_track_file():
    data_dir = get_data_dir()
    return os.path.join(data_dir, TIME_TRACK_FILE)


# TODO more functionality
# - save dates when worked on file (first, last or every date...)
# - hours/day
"""
persist_time_info()
    this method is responsible for converting and 
    saving the blend files time property to the disk
"""
def persist_time_info(tracking_file, timing_obj):
    data = {}
    if os.path.exists(tracking_file):
        data = read_json(tracking_file)
    
    blend_file = bpy.data.filepath
    if not blend_file:
        return False

    #data[blend_file] = { "seconds": time, "time": get_time_pretty(seconds=time)}
    data.update(timing_obj.to_dict())

    write_json(data, tracking_file)
    print(f"Saving time tracking data {data[blend_file]} in {tracking_file}")

    return True


# ADVANCED TIMING ENGINE

class TimingModel():
    def __init__(self, blend_file: str, seconds: int, sessions):
        self.blend_file = blend_file
        self.seconds = seconds
        self.time_formatted = get_time_pretty(seconds=self.seconds)
        self.sessions = sessions
        
        #LEGACY
        if not self.sessions and self.seconds > 0 and blend_file:
            self.add_session(session_seconds=self.seconds, date="Before")


    def get_new_session_id(self) -> int:
        if not self.sessions:
            return 0
        return max(session["id"] for session in self.sessions) + 1    


    def add_session(self, session_seconds: int, date: str = d.today().strftime('%Y-%m-%d')):
        dates = []
        dates.append(date)
        session_id = self.get_new_session_id()

        session = {
            "id": session_id,
            "dates": dates,
            "seconds": session_seconds,
        }
        self.sessions.append(session)
        print(f"Session added {session['id']}")

    """
    updates current session
    (if required at some point add 'session' parameter)
    """
    def update_session(self, seconds, session_seconds: int):
        session = self.get_current_session()
        if not session:
            return
        self.seconds = seconds
        self.time_formatted = get_time_pretty(seconds=self.seconds)

        session["seconds"] = session_seconds

        date: str = d.today().strftime('%Y-%m-%d')
        if date not in session["dates"]:
            session["dates"].append(date)

        #print(f"Session updated {session['id']}")
    

    def get_current_session(self):
        return self.sessions[-1] if len(self.sessions) > 0 else None


    def remove_session(self, session_id: int):
        self.sessions = [s for s in self.sessions if s["id"] != session_id]
    
    
    def reset_time(self):
        self.seconds = 0
        self.time_formatted = get_time_pretty(seconds=self.seconds)
        self.sessions = []
        self.add_session(0)


    def to_dict(self) -> dict:
        return {
            self.blend_file: {
                "seconds": self.seconds,
                "sessions": self.sessions
            }
        }
    
    
    @classmethod
    def from_dict(cls, blend_file: str, seconds: int = 0, sessions = []):
        return cls(blend_file, seconds, sessions)
    

    @classmethod
    def load_single_from_json(cls, file_path: str, blend_file: str):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if blend_file in data:
                content = data[blend_file]
                return cls(blend_file, content.get("seconds", 0), content.get("sessions", []))
        except Exception as e:
            print(e)
        return None
    