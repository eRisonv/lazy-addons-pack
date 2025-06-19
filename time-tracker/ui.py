import bpy

from .time_tracker import tt
from .functions import get_properties, get_time_pretty

class UI_TimeTracker(bpy.types.Panel):
    """Creates a Panel in the scene context of sidebar"""
    bl_label = "Time Tracker"
    bl_idname = "SCENE_PT_timetracker_panel"
    bl_space_type = 'VIEW_3D'  # Correct space type for the 3D View
    bl_region_type = 'UI'  # 'UI' is the region type for the Sidebar
    bl_context = "objectmode"  # You can change this depending on the context where you want the panel to appear
    bl_category = "Time Tracker"

    def draw(self, context):
        props = get_properties(context)
        layout = self.layout

        scene = context.scene

        box = layout.box()
        row = box.row()
        row.label(text="Time:")
        row.label(text=tt.get_work_time(props))
        row = box.row()
        row.label(text="Session Time:")
        row.label(text=tt.get_session_time(props))
        
        box.prop(props, 'stopp_and_go', text="Stopp & Go")
        if not props.stopp_and_go:
            if props.tracking:
                box.operator("time_tracker.pause", icon='PAUSE', text='Pause')
            else:
                box.operator("time_tracker.continue", icon='PLAY', text='Continue (paused)')

        box = layout.box()
        box.operator("time_tracker.show_time_table", text="Show Time Table")

class SettingsPanel(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "SCENE_PT_timetracker_settings_panel"
    bl_space_type = 'VIEW_3D'  # Correct space type for the 3D View
    bl_region_type = 'UI'  # 'UI' is the region type for the Sidebar
    bl_context = "objectmode"  # You can change this depending on the context where you want the panel to appear
    bl_category = "Time Tracker"
    bl_parent_id = "SCENE_PT_timetracker_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = get_properties(context)
        layout = self.layout

        if bpy.context.preferences.filepaths.use_auto_save_temporary_files:
            layout.prop(props, "autosave_compatibility")

        layout.operator("time_tracker.reset_time", text="Reset time") # WARNING!

class SessionPanel(bpy.types.Panel):
    bl_label = "Sessions"
    bl_idname = "SCENE_PT_timetracker_session_panel"
    bl_space_type = 'VIEW_3D'  # Correct space type for the 3D View
    bl_region_type = 'UI'  # 'UI' is the region type for the Sidebar
    bl_context = "objectmode"  # You can change this depending on the context where you want the panel to appear
    bl_category = "Time Tracker"
    bl_parent_id = "SCENE_PT_timetracker_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = get_properties(context)
        layout = self.layout

        layout.prop(props, "session_sort", text="Sort")
        layout.prop(props, "session_filter", text="Filter")

        sessions = tt.get_all_sessions()
        if not sessions:
            layout.label(text="No Sessions Yet")
            return
        
        list = sessions[::-1] if props.session_sort == '0' else sessions
        for session in list:
            if not filter_valid(session, props.session_filter):
                continue

            box = layout.box()
            row = box.row()
            row.alignment = "LEFT"
            row.label(text=f"Session: {session['id']}")
            row.label(text=' '.join(session["dates"]))
            box = box.box()
            
            box.label(text=f"{get_time_pretty(session['seconds'])}")

def filter_valid(session, filter):
    if not filter:
        return True
    
    for date in session["dates"]:
        if filter.lower() in date.lower():
            return True
    
    try:
        if session["id"] == int(filter):
            return True
    except Exception as e:
        pass
    
    return False