import bpy
from bpy.props import (BoolProperty, FloatVectorProperty, StringProperty, PointerProperty)
from bpy.types import (PropertyGroup)

class EaSel_Properties(PropertyGroup):
    easel_button: BoolProperty(
        name="",
        description="Silhouette on|off",
        default=True,
        update=lambda self, context: self.athing(context)
    )

    # Свойства для хранения предыдущих настроек
    prev_background_type: StringProperty()
    prev_background_color: FloatVectorProperty(subtype='COLOR', size=3)
    prev_shading_type: StringProperty()
    prev_light: StringProperty()
    prev_color_type: StringProperty()
    prev_single_color: FloatVectorProperty(subtype='COLOR', size=3)
    prev_show_overlays: BoolProperty()
    prev_show_shadows: BoolProperty()
    prev_show_cavity: BoolProperty()
    prev_settings_saved: BoolProperty(default=False)  # Новое свойство

    def athing(self, context):
        print(f"\n=== Property Update Triggered ===")
        print(f"New Button State: {self.easel_button}")
        print(f"Settings Saved Flag: {self.prev_settings_saved}")
        
        if self.easel_button:
            bpy.ops.easel.silhouette_on()
        else:
            bpy.ops.easel.silhouette_off()
    
def register():
    try:
        bpy.utils.register_class(EaSel_Properties)
    except ValueError:
        bpy.utils.unregister_class(EaSel_Properties)
        bpy.utils.register_class(EaSel_Properties)
    bpy.types.Scene.easel_prop = PointerProperty(type=EaSel_Properties)

def unregister():
    try:
        bpy.utils.unregister_class(EaSel_Properties)
    except ValueError:
        pass
    if hasattr(bpy.types.Scene, "easel_prop"):
        del bpy.types.Scene.easel_prop