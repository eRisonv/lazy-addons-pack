import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent

from .time_tracker import tt
from .functions import get_properties, get_time_pretty

# Viewport overlay drawing function
def draw_timer_overlay(context):
    """Draw timer overlay in viewport"""
    # Получаем настройки из аддона
    try:
        prefs = context.preferences.addons[__package__].preferences
    except KeyError:
        print(f"Error: Addon {__package__} not found in preferences")
        return
    
    # Только рисуем, если включено в настройках аддона
    if not prefs.show_viewport_timer:
        print("Viewport timer disabled, skipping draw")
        return
    
    props = get_properties(context)
    
    # Get viewport dimensions
    region = context.region
    if not region:
        print("Error: No valid region found for drawing")
        return
    
    # Get timer text
    timer_text = f"Time: {tt.get_work_time(props)}"
    session_text = f"Session: {tt.get_session_time(props)}"
    
    # Font settings to match Blender's Statistics overlay
    font_id = 0
    font_size = 11
    
    # Calculate text dimensions
    blf.size(font_id, font_size)
    timer_width = blf.dimensions(font_id, timer_text)[0]
    session_width = blf.dimensions(font_id, session_text)[0]
    text_height = blf.dimensions(font_id, timer_text)[1]
    
    # Calculate position based on settings
    margin = 10
    line_spacing = 4
    
    # Determine position with both horizontal and vertical offsets
    if prefs.viewport_timer_position == 'BOTTOM_RIGHT':
        x = region.width - max(timer_width, session_width) - margin + prefs.viewport_timer_offset_x
        y = margin + prefs.viewport_timer_offset_y
    elif prefs.viewport_timer_position == 'BOTTOM_LEFT':
        x = margin + prefs.viewport_timer_offset_x
        y = margin + prefs.viewport_timer_offset_y
    elif prefs.viewport_timer_position == 'TOP_RIGHT':
        x = region.width - max(timer_width, session_width) - margin + prefs.viewport_timer_offset_x
        y = region.height - (text_height * 2 + line_spacing) - margin - prefs.viewport_timer_offset_y
    else:  # TOP_LEFT
        x = margin + prefs.viewport_timer_offset_x
        y = region.height - (text_height * 2 + line_spacing) - margin - prefs.viewport_timer_offset_y
    
    # Clamp positions to viewport bounds
    x = max(0, min(x, region.width - max(timer_width, session_width)))
    y = max(0, min(y, region.height - (text_height * 2 + line_spacing)))
    
    # Draw background if enabled
    if prefs.viewport_timer_background:
        try:
            # Initialize GPU context
            gpu.state.blend_set('ALPHA')
            
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            
            # Background rectangle coordinates
            bg_margin = 4
            bg_x1 = x - bg_margin
            bg_y1 = y - bg_margin
            bg_x2 = x + max(timer_width, session_width) + bg_margin
            bg_y2 = y + (text_height * 2 + line_spacing) + bg_margin
            
            # Validate coordinates
            if bg_x1 >= bg_x2 or bg_y1 >= bg_y2:
                print(f"Error: Invalid background coordinates: x1={bg_x1}, x2={bg_x2}, y1={bg_y1}, y2={bg_y2}")
                return
            
            vertices = [
                (bg_x1, bg_y1),
                (bg_x2, bg_y1),
                (bg_x2, bg_y2),
                (bg_x1, bg_y2)
            ]
            
            indices = [(0, 1, 2), (2, 3, 0)]
            
            batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
            
            shader.bind()
            # Use a more visible alpha for background
            alpha = min(max(prefs.viewport_timer_text_alpha * 0.5, 0.2), 0.9)
            shader.uniform_float("color", (0.0, 0.0, 0.0, alpha))
            batch.draw(shader)
            
            # Reset GPU state
            gpu.state.blend_set('NONE')
        except Exception as e:
            print(f"Error drawing background: {e}")
    
    # Set text color
    if props.tracking:
        text_color = (1.0, 1.0, 1.0, min(max(prefs.viewport_timer_text_alpha, 0.1), 1.0))  # White when tracking
    else:
        text_color = (1.0, 1.0, 0.0, min(max(prefs.viewport_timer_text_alpha, 0.1), 1.0))  # Yellow when paused
    
    # Draw text with black outline
    outline_color = (0.0, 0.0, 0.0, min(max(prefs.viewport_timer_text_alpha, 0.1), 1.0))
    outline_offset = 1.0
    
    try:
        # Draw timer text outline
        for dx, dy in [(outline_offset, 0), (-outline_offset, 0), (0, outline_offset), (0, -outline_offset)]:
            blf.position(font_id, x + dx, y + text_height + line_spacing + dy, 0)
            blf.color(font_id, *outline_color)
            blf.draw(font_id, timer_text)
            
            blf.position(font_id, x + dx, y + dy, 0)
            blf.color(font_id, *outline_color)
            blf.draw(font_id, session_text)
        
        # Draw timer text
        blf.position(font_id, x, y + text_height + line_spacing, 0)
        blf.color(font_id, *text_color)
        blf.draw(font_id, timer_text)
        
        # Draw session text
        blf.position(font_id, x, y, 0)
        blf.color(font_id, *text_color)
        blf.draw(font_id, session_text)
    except Exception as e:
        print(f"Error drawing text with outline: {e}")

# Handler to register/unregister overlay
_draw_handler = None

def register_viewport_overlay():
    """Register viewport overlay"""
    global _draw_handler
    if _draw_handler is None:
        _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_timer_overlay, (bpy.context,), 'WINDOW', 'POST_PIXEL'
        )
        # Force viewport redraw
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        print("Viewport overlay registered")

def unregister_viewport_overlay():
    """Unregister viewport overlay"""
    global _draw_handler
    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
        # Force viewport redraw
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        print("Viewport overlay unregistered")

@persistent
def load_post_handler(dummy):
    """Re-register overlay after file load"""
    if hasattr(bpy.context, 'preferences') and __package__ in bpy.context.preferences.addons:
        prefs = bpy.context.preferences.addons[__package__].preferences
        if prefs.show_viewport_timer:
            register_viewport_overlay()
            print("Viewport overlay re-registered on file load")

# Viewport timer toggle operator
class TIME_TRACKER_OT_toggle_viewport_timer(bpy.types.Operator):
    bl_idname = "time_tracker.toggle_viewport_timer"
    bl_label = "Toggle Viewport Timer"
    bl_description = "Toggle timer display in viewport"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        
        if prefs.show_viewport_timer:
            register_viewport_overlay()
            self.report({'INFO'}, "Viewport timer enabled")
        else:
            unregister_viewport_overlay()
            self.report({'INFO'}, "Viewport timer disabled")
        
        return {'FINISHED'}

def register():
    bpy.app.handlers.load_post.append(load_post_handler)
    print("Viewport overlay handlers registered")

def unregister():
    unregister_viewport_overlay()
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    print("Viewport overlay handlers unregistered")