from . import WireColorTools


bl_info = {
	"name": "Wireframe Color Tools",
	"author": "Johannes Kollmer",
	"version": (1,0),
	"blender": (2, 93, 0),
	"location": "Properties > Object Tab",
	"description": "Change Wireframe Colors based on different kinds of methods",
	"category": "3D View",
}

def register():
    WireColorTools.register()
    
def unregister():
    WireColorTools.unregister()