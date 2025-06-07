import bpy
import os


def draw_item(self, context):
    easel_tool = context.scene.easel_prop
    
    pcoll = preview_collections["main"]
    EaSel_ON = pcoll["EaSel_ON"]
    EaSel_OFF = pcoll["EaSel_OFF"]
    
    layout = self.layout
    layout.prop(easel_tool, 'easel_button', text="", icon_value=pcoll["EaSel_ON"].icon_id if easel_tool.easel_button else pcoll["EaSel_OFF"].icon_id)
      

preview_collections = {}
def register():
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")

    pcoll.load("EaSel_ON", os.path.join(my_icons_dir, "EaSel_ON.png"), 'IMAGE')
    pcoll.load("EaSel_OFF", os.path.join(my_icons_dir, "EaSel_OFF.png"), 'IMAGE')
    preview_collections["main"] = pcoll   
    
    bpy.types.VIEW3D_HT_header.append(draw_item)


def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
    
    bpy.types.VIEW3D_HT_header.remove(draw_item)