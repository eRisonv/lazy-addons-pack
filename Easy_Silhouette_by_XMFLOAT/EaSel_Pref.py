import bpy
import os
from bpy.types import AddonPreferences
from bpy.props import FloatVectorProperty

class EaSel_Links(AddonPreferences):
    bl_idname = "Easy_Silhouette_by_XMFLOAT"

    mesh_color: FloatVectorProperty(
        subtype='COLOR', 
        default=(0.0, 0.0, 0.0), 
        min=0.0, 
        max=1.0, 
        size=3
    )
    
    background_color: FloatVectorProperty(
        subtype='COLOR', 
        default=(1.0, 1.0, 1.0),  
        min=0.0, 
        max=1.0, 
        size=3
    )

    def draw(self, context):
        layout = self.layout
        pcoll = preview_collections["main"]
        
        # Color Settings
        box = layout.box()
        box.label(text="Color Settings:")
        col = box.column()
        col.prop(self, 'mesh_color', text="Mesh color")
        col.prop(self, 'background_color', text="Background color") 
        
        # Links
        box = layout.box()
        box.label(text='Links:')
        box.operator('wm.url_open', text='Artstation', icon_value=pcoll["Artstation"].icon_id).url = 'https://www.artstation.com/xmfloat'

classes = (
    EaSel_Links,
)

preview_collections = {}

def register():
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    
    pcoll.load("Artstation", os.path.join(my_icons_dir, "Artstation.png"), 'IMAGE')
    preview_collections["main"] = pcoll   
    
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()