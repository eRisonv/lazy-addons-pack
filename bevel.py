bl_info = {
    "name": "Custom Bevel Defaults",
    "author": "Custom Bevel Expert", 
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Automatic",
    "description": "Automatically sets custom Bevel modifier defaults with configurable settings",
    "category": "Modifier",
}

import bpy
import math
from bpy.app.handlers import persistent

@persistent
def override_bevel_defaults(scene, depsgraph):
    """Automatically override bevel modifier settings when added"""
    apply_bevel_settings()

@persistent
def override_bevel_on_load(dummy):
    """Apply settings on file load"""
    apply_bevel_settings()

def is_mesh_smooth_shaded(obj):
    """Check if mesh already has smooth shading applied"""
    if not obj.data.polygons:
        return False
    
    # Check if all polygons are smooth
    return all(poly.use_smooth for poly in obj.data.polygons)

def apply_bevel_settings():
    """Apply custom bevel settings to all applicable bevel modifiers"""
    
    # Get addon preferences safely
    try:
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
    except:
        return  # Addon not properly loaded yet
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'BEVEL':
                    # Check if this bevel has default settings (needs to be changed)
                    if (mod.miter_outer == 'MITER_SHARP' and 
                        mod.use_clamp_overlap == True and 
                        mod.loop_slide == True and
                        mod.segments == 1):  # Default segments is 1
                        
                        # Apply custom settings from preferences
                        mod.segments = addon_prefs.segments
                        mod.miter_outer = addon_prefs.miter_type
                        mod.use_clamp_overlap = addon_prefs.clamp_overlap
                        mod.loop_slide = addon_prefs.loop_slide
                        
                        # Apply Auto Smooth if enabled
                        if addon_prefs.apply_auto_smooth:
                            # Check if mesh is already smooth shaded
                            mesh_already_smooth = is_mesh_smooth_shaded(obj)
                            # Check if auto smooth is already enabled
                            auto_smooth_already_set = obj.data.use_auto_smooth
                            
                            # Only apply shading changes if mesh doesn't have smooth shading or auto smooth
                            if not mesh_already_smooth or not auto_smooth_already_set:
                                # Save current selection and mode
                                current_mode = bpy.context.mode
                                selected_objects = bpy.context.selected_objects
                                active_object = bpy.context.active_object
                                
                                # Switch to object mode if needed
                                if current_mode != 'OBJECT':
                                    bpy.ops.object.mode_set(mode='OBJECT')
                                
                                # Select and activate the object
                                bpy.ops.object.select_all(action='DESELECT')
                                obj.select_set(True)
                                bpy.context.view_layer.objects.active = obj
                                
                                # Apply Shade Smooth only if not already smooth
                                if not mesh_already_smooth:
                                    bpy.ops.object.shade_smooth()
                                    print(f"Applied shade smooth to {obj.name} (was not smooth)")
                                else:
                                    print(f"Skipped shade smooth for {obj.name} (already smooth)")
                                
                                # Enable Auto Smooth with custom angle only if not already set
                                if not auto_smooth_already_set:
                                    import math
                                    obj.data.use_auto_smooth = True
                                    obj.data.auto_smooth_angle = math.radians(addon_prefs.auto_smooth_angle)
                                    print(f"Applied auto smooth {addon_prefs.auto_smooth_angle}° to {obj.name}")
                                else:
                                    print(f"Skipped auto smooth for {obj.name} (already enabled with {math.degrees(obj.data.auto_smooth_angle):.1f}°)")
                                
                                # Restore previous selection and mode
                                bpy.ops.object.select_all(action='DESELECT')
                                for sel_obj in selected_objects:
                                    sel_obj.select_set(True)
                                if active_object:
                                    bpy.context.view_layer.objects.active = active_object
                                if current_mode != 'OBJECT':
                                    bpy.ops.object.mode_set(mode=current_mode.replace('_', ''))
                            else:
                                print(f"Skipped all shading changes for {obj.name} (already has smooth shading and auto smooth)")
                        
                        print(f"Applied custom bevel defaults to {obj.name}: segments={addon_prefs.segments}, miter={addon_prefs.miter_type}, clamp={addon_prefs.clamp_overlap}, slide={addon_prefs.loop_slide}, auto_smooth={addon_prefs.apply_auto_smooth}, angle={addon_prefs.auto_smooth_angle}°")

# Timer function for periodic checks
def check_bevel_modifiers():
    """Periodic check for new bevel modifiers"""
    apply_bevel_settings()
    return 1.0  # Check every second

class CustomBevelPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    # Bevel settings
    segments: bpy.props.IntProperty(
        name="Segments",
        description="Number of segments for bevel",
        default=2,
        min=1,
        max=50
    )
    
    miter_type: bpy.props.EnumProperty(
        name="Miter Type",
        description="Miter type for bevel",
        items=[
            ('MITER_SHARP', 'Sharp', 'Sharp miter'),
            ('MITER_PATCH', 'Patch', 'Patch miter'),
            ('MITER_ARC', 'Arc', 'Arc miter')
        ],
        default='MITER_ARC'
    )
    
    clamp_overlap: bpy.props.BoolProperty(
        name="Clamp Overlap",
        description="Clamp overlap for bevel",
        default=False
    )
    
    loop_slide: bpy.props.BoolProperty(
        name="Loop Slide",
        description="Loop slide for bevel",
        default=False
    )
    
    # Shading setting
    apply_auto_smooth: bpy.props.BoolProperty(
        name="Apply Auto Smooth",
        description="Automatically apply Auto Smooth with angle when adding bevel",
        default=True
    )
    
    auto_smooth_angle: bpy.props.FloatProperty(
        name="Auto Smooth Angle",
        description="Auto smooth angle in degrees",
        default=60.0,
        min=0.0,
        max=180.0
    )
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Custom Bevel Modifier Settings:")
        
        # Bevel settings
        box = layout.box()
        box.label(text="Bevel Settings:")
        box.prop(self, "segments")
        box.prop(self, "miter_type")
        box.prop(self, "clamp_overlap")
        box.prop(self, "loop_slide")
        
        # Shading settings
        box = layout.box()
        box.label(text="Shading Settings:")
        box.prop(self, "apply_auto_smooth")
        if self.apply_auto_smooth:
            box.prop(self, "auto_smooth_angle")
        
        layout.separator()
        layout.label(text="Simply add Bevel modifiers as usual - custom settings will be applied automatically!")
        layout.label(text="Note: Addon preserves existing smooth shading on meshes.")

# Registration
classes = (
    CustomBevelPreferences,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add multiple handlers for better coverage
    if override_bevel_defaults not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(override_bevel_defaults)
    
    if override_bevel_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(override_bevel_on_load)
    
    # Start periodic timer check
    bpy.app.timers.register(check_bevel_modifiers, persistent=True)
    
    print("Custom Bevel Defaults addon registered - Bevel modifiers will use custom defaults automatically")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Remove handlers
    if override_bevel_defaults in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(override_bevel_defaults)
    
    if override_bevel_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(override_bevel_on_load)
    
    # Stop timer
    if bpy.app.timers.is_registered(check_bevel_modifiers):
        bpy.app.timers.unregister(check_bevel_modifiers)
    
    print("Custom Bevel Defaults addon unregistered")

if __name__ == "__main__":
    register()