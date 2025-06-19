import time
import bpy
from datetime import datetime, timedelta

from .functions import TimingModel, get_properties, get_time_pretty, get_time_track_file, persist_time_info, read_json
from .properties import LOGGER_DISABLED, LOGGER_RUNNING, LOGGER_SLEEPING

# TODO groups for blend files (time table etc.)
# TODO tracking hours per day with dates etc.
 
class TIME_TRACKER_OT_pause(bpy.types.Operator):
    bl_idname = "time_tracker.pause"
    bl_label = "Pause"
    bl_description = "Pause Time Tracking"

    def execute(self, context):
        props = get_properties(context)

        props.tracking = False

        self.report({'INFO'}, f"Time Tracking paused")
        return {'FINISHED'}
    

class TIME_TRACKER_OT_continue(bpy.types.Operator):
    bl_idname = "time_tracker.continue"
    bl_label = "Continue"
    bl_description = "Continue Time Tracking"

    def execute(self, context):
        props = get_properties(context)

        props.tracking = True
        
        self.report({'INFO'}, f"Time Tracking continued")
        return {'FINISHED'}
    

class TIME_TRACKER_OT_time_table(bpy.types.Operator):
    bl_idname = "time_tracker.show_time_table"
    bl_label = "Time Table"
    bl_description = "Time table data of all tracked projects"

    _width = 600

    def execute(self, context):
        return {'FINISHED'}
    
    # Dialog-Inhalt
    def draw(self, context):
        layout = self.layout

        # save current time before reading
        tt.save()

        data = read_json(get_time_track_file())

        if not data:
            layout.label(text="No tracked files yet.", icon='INFO')
            return

        for file, attributes in data.items():
            box = layout.box()
            box.label(text=file)
            box.label(text=f"{get_time_pretty(attributes['seconds'])}")
            

    def invoke(self, context, event):
        # Öffnet eine Popup-Form

        # Holen der aktuellen Bildschirmgröße
        screen_width = context.window.width
        screen_height = context.window.height

        # Fenstergröße des Dialogs
        dialog_width = self._width
        dialog_height = 0

        # Berechnen der zentrierten Position
        center_x = (screen_width - dialog_width) // 2
        center_y = (screen_height - dialog_height) // 2

        # Position des Dialogs setzen
        context.window.cursor_warp(center_x, center_y)
        return context.window_manager.invoke_props_dialog(self, width=600)
    

class TIME_TRACKER_OT_reset_time(bpy.types.Operator):
    bl_idname = "time_tracker.reset_time"
    bl_label = "Reset Time"
    bl_description = "Resets time data of the tracked file"

    def execute(self, context):
        props = get_properties(context)
        tt.reset_time(props)

        self.report({'INFO'}, f"Time data deleted. Starting at {props.time}.")
        return {'FINISHED'}
    
    # Dialog-Inhalt
    def draw(self, context):
        layout = self.layout
        layout.label(text="This will delete this files' time data!", icon='ERROR')  # Changed WARNING to ERROR
            
    def invoke(self, context, event):
        # Öffnet eine Popup-Form
        return context.window_manager.invoke_props_dialog(self)
    

   
# TODO if file changes might interfere w/ last inter time - reset on load_file?
class TimeTracker():
    _timing_obj: TimingModel = None
    _last_timing = 0
    _last_interaction_time = 0
    
    _last_tracking_stop = {
        "start": None,
        "stop": None
    }

    def __init__(self):
        self._last_timing = time.time()
        #TODO get props.time from file and (if existing and greater) ask user to overwrite/use existing time track from file <- Blend File always stays "Master"

    """
    Get session from tracking file or create new with property time
    """
    def load_session(self, seconds: int = 0):
        self._timing_obj = TimingModel.load_single_from_json(file_path=get_time_track_file(), blend_file=bpy.data.filepath)
        if not self._timing_obj:
            self._timing_obj = TimingModel(blend_file=bpy.data.filepath, seconds=seconds, sessions=[])
            
        self._timing_obj.add_session(0)
        print("Session loaded")


    def get_work_time(self, props, pretty: bool = True) -> str:
        if not pretty:
            return props.time
        return get_time_pretty(seconds=props.time)


    def get_session_time(self, props, pretty: bool = True) -> str:
        if not pretty:
            return props.session_time
        return get_time_pretty(seconds=props.session_time)

    """
    updates overall time and session through blend properties & Timing Data Interface "TimingModel"
    """
    def update_time(self, props, logger_state):
        now = int(time.time()) # only seconds needed 
        if now == self._last_timing:
            return 0 # prevent 'washing' the last timestamp
        
        diff = int(now - self._last_timing)
        self._last_timing = now

        # set inactive (stop)
        if props.stopp_and_go:
            self.stopp_and_go(props, now, logger_state) # set props.tracking autom.
            
        if props.tracking:
            # Blender Properties
            props.time = props.time + diff
            props.session_time = props.session_time + diff
            # I/O
            try:
                if not self._timing_obj or bpy.data.filepath != self._timing_obj.blend_file:
                    self.load_session(props.time)

                # file overwrites blender prop
                #if self._timing_obj.seconds > props.time:
                #    props.time = self._timing_obj.seconds

                self._timing_obj.update_session(props.time, props.session_time)

            except Exception as e:
                print(e)
        
        return props.time
    

    def stopp_and_go(self, props, now, logger_state: int = LOGGER_RUNNING):
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
        except KeyError:
            print(f"Error: Addon {__package__} not found in preferences")
            return

        if props.tracking and logger_state == LOGGER_SLEEPING:
            track_last_interaction()
            print("Assuming activity...")
            return

        if self._last_interaction_time > 0 and (now - self._last_interaction_time) > prefs.interaction_threshhold:
            # USER INACTIVE
            if props.tracking:
                props.time = props.time - prefs.interaction_threshhold
                props.session_time = props.session_time - prefs.interaction_threshhold
                print(f"{props.time} {prefs.interaction_threshhold}")
                local_time = datetime.now() - timedelta(seconds=prefs.interaction_threshhold)
                print(f"Not tracking due to inactivity. Stopped tracking at {local_time.strftime('%H:%M:%S')} - session time: {tt.get_session_time(props)}")
            props.tracking = False
            return

        # USER ACTIVE
        if not props.tracking:
            print(f"Resume tracking {datetime.now().strftime('%H:%M:%S')}")
            props.tracking = True


    def get_all_sessions(self):
        return self._timing_obj.sessions if self._timing_obj else None


    def reset_time(self, props):
        props.time = 0
        props.session_time = 0
        self._timing_obj.reset_time()
        self.save()


    def save(self):
        return persist_time_info(get_time_track_file(), self._timing_obj)

tt = TimeTracker()

_last_autosave_check = time.time()


# TODO modal operator is blocking blenders autosave function - use keymaps? or too specific??
# with the compatibility mode it's likely the user will have a delayed interactivity detection (bc. modal operator is shut down atm.) 
# TODO settings - delay / compatibility on/off ?
# https://blender.stackexchange.com/questions/267285/alternative-to-modal-operators-blocked-autosave?utm_source=chatgpt.com
class ModalEventLoggerOperator(bpy.types.Operator):
    """Checks user interaction with blender for stopp & go function"""
    bl_idname = "wm.modal_event_logger"
    bl_label = "Modal Event Logger"

    def modal(self, context, event):
        props = get_properties(context)
        try:
            prefs = context.preferences.addons[__package__].preferences
        except KeyError:
            print(f"Error: Addon {__package__} not found in preferences")
            return {'CANCELLED'}

        if props.autosave_compatibility and bpy.context.preferences.filepaths.use_auto_save_temporary_files and check_autosave():
            # Restart modal operator so blender autosave can happen in between stop & restart
            self.restart(context, delay=11)
            return {'CANCELLED'}

        if not props.stopp_and_go: # TODO optimize shutdown (less code when running)
            self.cancel(context)
            return {'CANCELLED'}

        track_last_interaction()

        # Weiterleiten des Events
        return {'PASS_THROUGH'}

    def execute(self, context):
        if context.window_manager.get("modal_logger_state", LOGGER_DISABLED) == LOGGER_RUNNING:
            self.report({'WARNING'}, "Modal Logger already running!")
            
        context.window_manager.modal_handler_add(self)
        context.window_manager["modal_logger_state"] = LOGGER_RUNNING

        print(f"Logger started {datetime.now().strftime('%H:%M:%S')}")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager["modal_logger_state"] = LOGGER_DISABLED
        print(f"Logger stopped {datetime.now().strftime('%H:%M:%S')}")

    def restart(self, context, delay):
        context.window_manager["modal_logger_state"] = LOGGER_SLEEPING
        print(f"Logger sleeping {datetime.now().strftime('%H:%M:%S')}")
        bpy.app.timers.register(revive_logger, first_interval=delay)

    def invoke(self, context, event):
        return self.execute(context)


def check_autosave():
    global _last_autosave_check

    if not bpy.data.is_dirty:
        # no dirty data, no autosave
        _last_autosave_check = time.time()
        return False
    
    intervall = bpy.context.preferences.filepaths.auto_save_time * 60
    diff = time.time() - _last_autosave_check - intervall
    if not diff > 0:
        # autosave interval not reached
        return False

    print(f"Autosave is pending")
    _last_autosave_check = time.time()
    return True
    

def revive_logger():
    print(f"Reviving Logger...")
    bpy.ops.wm.modal_event_logger()
    return None


import time
def track_last_interaction():
    try:
        tt._last_interaction_time = int(time.time())  # Setze den Zeitstempel auf den aktuellen Zeitpunkt
        #print(f"Letzte Interaktion: {tt._last_interaction_time}")
    except Exception as e:
        print(f"Last interaction not documented. Error {e}.")

def init():
    try:
        c = bpy.context
        if not c.scene:
            print("Init - try again...")
            return 0.1
        props = c.scene.time_tracker_props
        if bpy.data.filepath:
            props.session_time = 0
        props.tracking = True
        bpy.ops.wm.modal_event_logger()
        
        # Initialize viewport overlay if enabled
        if c.preferences.addons[__package__].preferences.show_viewport_timer:
            from . import viewport_overlay
            viewport_overlay.register_viewport_overlay()
            
        print(f"Init")
    except Exception as e:
        print(e)
    
    return None