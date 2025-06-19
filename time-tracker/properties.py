import bpy

from .functions import get_properties

# BLENDER PROPERTIES

TIME_TRACK_FILE = 'time_tracks.json'

LOGGER_DISABLED = "0"
LOGGER_RUNNING = "1"
LOGGER_SLEEPING = "2" # actually disabled but waiting for revive

def toggle_stop_and_go(self, context):
    try:
        props = get_properties(context)
        if props.stopp_and_go:
            bpy.ops.wm.modal_event_logger()
        # else: logger will shutdown itself
    except Exception as e:
        print(e)

def toggle_viewport_timer(self, context):
    """Toggle viewport timer overlay"""
    try:
        # Import here to avoid circular imports
        from . import viewport_overlay
        
        if self.show_viewport_timer:
            viewport_overlay.register_viewport_overlay()
        else:
            viewport_overlay.unregister_viewport_overlay()
    except Exception as e:
        print(f"Error toggling viewport timer: {e}")

def update_viewport_timer_settings(self, context):
    """Update viewport when timer settings change"""
    try:
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except Exception as e:
        print(f"Error updating viewport timer settings: {e}")

class TimeTrackerProperties(bpy.types.PropertyGroup):
    time: bpy.props.IntProperty(
        name="time",
        description="Time spent working on this file",
        default=0
    ) # type: ignore

    session_time: bpy.props.IntProperty(
        name="session time",
        description="Time spent on this file in one session",
        default=0
    ) # type: ignore

    tracking: bpy.props.BoolProperty(
        name="is_tracking",
        description="Returns if time tracking is running",
        default=True
    ) # type: ignore
    
    stopp_and_go: bpy.props.BoolProperty(
        name="stopp and go",
        description="Detects inactivity based on threshhold and stopps/starts tracking",
        default=True,
        update=toggle_stop_and_go
    ) # type: ignore

    autosave_compatibility: bpy.props.BoolProperty(
        name="autosave compatibility mode",
        description="Shuts down modal operator for a moment (autosave interval) allowing blender to perform autosave (might affect 'stopp & go' user experience)",
        default=True
    ) # type: ignore

    session_sort: bpy.props.EnumProperty(
        name="Sort",
        description="sort sessions",
        items=[('0', "Latest first", ""), ('1', "Oldest first", "")],
        default='0'
    ) # type: ignore

    session_filter: bpy.props.StringProperty(
        name="Filter",
        description="Filter sessions (id, date)",
        default=""
    ) # type: ignore

class TimeTrackerPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_viewport_timer: bpy.props.BoolProperty(
        name="Show Viewport Timer",
        description="Display timer in viewport overlay (like Statistics)",
        default=False,
        update=toggle_viewport_timer
    ) # type: ignore

    interaction_threshhold: bpy.props.IntProperty(
        name="Inactivity Threshold",
        description="Threshold of inactivity (when to stop timing) in seconds",
        default=120,
        min=15,
        max=3600
    ) # type: ignore

    viewport_timer_position: bpy.props.EnumProperty(
        name="Timer Position",
        description="Position of timer in viewport",
        items=[
            ('BOTTOM_RIGHT', "Bottom Right", "Position timer at bottom right of viewport"),
            ('BOTTOM_LEFT', "Bottom Left", "Position timer at bottom left of viewport"),
            ('TOP_RIGHT', "Top Right", "Position timer at top right of viewport"),
            ('TOP_LEFT', "Top Left", "Position timer at top left of viewport")
        ],
        default='BOTTOM_RIGHT',
        update=update_viewport_timer_settings
    )

    viewport_timer_offset_x: bpy.props.IntProperty(
        name="Horizontal Offset",
        description="Horizontal offset for timer position (pixels)",
        default=0,
        min=-200,
        max=200,
        update=update_viewport_timer_settings
    )

    viewport_timer_offset_y: bpy.props.IntProperty(
        name="Vertical Offset",
        description="Vertical offset for timer position (pixels)",
        default=0,
        min=-200,
        max=200,
        update=update_viewport_timer_settings
    )

    viewport_timer_background: bpy.props.BoolProperty(
        name="Timer Background",
        description="Show semi-transparent background behind timer text",
        default=True,
        update=update_viewport_timer_settings
    )

    viewport_timer_text_alpha: bpy.props.FloatProperty(
        name="Transparency",
        description="Transparency of the timer text and background (0.0 = fully transparent, 1.0 = fully opaque)",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_viewport_timer_settings
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Time Tracker Settings")
        layout.prop(self, "show_viewport_timer")
        layout.prop(self, "interaction_threshhold")
        layout.label(text="Viewport Timer Settings")
        layout.prop(self, "viewport_timer_position")
        layout.prop(self, "viewport_timer_offset_x")
        layout.prop(self, "viewport_timer_offset_y")
        layout.prop(self, "viewport_timer_background")
        layout.prop(self, "viewport_timer_text_alpha")

# Registration-Funktionen, falls не автоматически регистрируется:
def register():
    print("Registering TimeTrackerProperties")  # For debugging
    bpy.types.Scene.time_tracker_props = bpy.props.PointerProperty(type=TimeTrackerProperties)
    print("TimeTrackerProperties registered")  # For debugging

def unregister():
    del bpy.types.Scene.time_tracker_props