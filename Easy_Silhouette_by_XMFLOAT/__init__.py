bl_info = {
    "name": "Easy Silhouette",
    "author": "XMFLOAT",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Header",
    "description": "Toggle silhouette mode with hotkey",
    "warning": "",
    "category": "3D View"
}

import bpy
from . import EaSel_Ops
from . import EaSel_Pref
from . import EaSel_Prop
from . import EaSel_UI

def register():
    EaSel_Prop.register()
    EaSel_Pref.register()
    EaSel_Ops.register()
    EaSel_UI.register() 

def unregister():
    EaSel_UI.unregister()
    EaSel_Ops.unregister()
    EaSel_Pref.unregister()
    EaSel_Prop.unregister()

if __name__ == "__main__":
    register()