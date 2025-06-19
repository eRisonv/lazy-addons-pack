bl_info = {
    "name": "Time Tracker",
    "author": "Gwyn",
    "version": (1, 0, 0),
    "blender": (4, 0, 2),
    "location": "View3D > Sidebar > Time Tracker",
    "description": "Tracks time spent on Blender projects with viewport overlay",
    "category": "Scene",
}

import bpy


from .functions import get_properties
from .properties import LOGGER_RUNNING
from .time_tracker import tt
from . import auto_load
from . import viewport_overlay
from bpy.app.handlers import persistent


@persistent
def load_handler(dummy):
    # TIME TRACK UPDATER
    if not bpy.app.timers.is_registered(track_timer):
        bpy.app.timers.register(track_timer, first_interval=0.1)
        
    if not bpy.app.timers.is_registered(init):
        bpy.app.timers.register(init, first_interval=0.1)



@persistent
def on_save_file(dummy):
    try:
        if not tt.save():
            print(f"Error. Cannot persist data of blend file {bpy.data.filepath}.")
    except Exception as e:
        print(f"Cannot save time tracking data: {e}")



# TIMER
def track_timer():
    try:
        context = bpy.context
        if context.scene:
            # ONLY HERE DO STH.
            props = get_properties(context)
            tt.update_time(props, context.window_manager.get("modal_logger_state", LOGGER_RUNNING))
            
            # Force viewport refresh when timer is visible
            # ИСПРАВЛЕНИЕ: используем prefs вместо props
            try:
                prefs = context.preferences.addons[__name__].preferences
                if prefs.show_viewport_timer:
                    # Only refresh 3D viewports to avoid performance issues
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
            except (KeyError, AttributeError):
                # Если preferences недоступны, просто пропускаем
                pass
            
            #print(f"Track timer is running...{time}")
    except Exception as e:
        print(f"Error in Time Tracker: {e}")

    return 1.0


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
        # ИСПРАВЛЕНИЕ: используем prefs вместо props
        try:
            prefs = c.preferences.addons[__name__].preferences
            if prefs.show_viewport_timer:
                viewport_overlay.register_viewport_overlay()
        except (KeyError, AttributeError):
            # Если preferences недоступны, просто пропускаем
            pass
            
        print(f"Init")
    except Exception as e:
        print(e)
    
    return None


# AUTO LOAD
auto_load.init()

def register():
    auto_load.register()
    viewport_overlay.register()

    # HANDLERS
    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.save_pre.append(on_save_file)

    # TIMERS
    if not bpy.app.timers.is_registered(track_timer):
        bpy.app.timers.register(track_timer, first_interval=0.1)
        
    if not bpy.app.timers.is_registered(init):
        bpy.app.timers.register(init, first_interval=0.1)


def unregister():
    # TIMERS
    if bpy.app.timers.is_registered(track_timer):
        bpy.app.timers.unregister(track_timer)

    if bpy.app.timers.is_registered(init):
        bpy.app.timers.unregister(init)

    # HANDLERS
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)

    if on_save_file in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(on_save_file)

    viewport_overlay.unregister()
    auto_load.unregister()