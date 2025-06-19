# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see http://www.gnu.org/licenses/
#  or write to the Free Software Foundation, Inc., 51 Franklin Street,
#  Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import bpy
import numpy
from mathutils import Vector


class WireFrameColorTools(bpy.types.PropertyGroup):

    wireColMin: bpy.props.FloatVectorProperty(default = (0.0, 0.5, 1.0), soft_min = 0, soft_max = 1, size = 3, subtype = 'COLOR')
    wireColMax: bpy.props.FloatVectorProperty(default = (1.0, 0.5, 0.0), soft_min = 0, soft_max = 1, size = 3, subtype = 'COLOR')
    wireColNew: bpy.props.FloatVectorProperty(soft_min = 0, soft_max = 1, size = 3, subtype = 'COLOR')
    wireColSet: bpy.props.FloatVectorProperty(default = (0.0, 0.5, 1.0), soft_min = 0, soft_max = 1, size = 3, subtype = 'COLOR')


class WireframeColorToolsPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Wireframe Color Tools"
    bl_idname = "OBJECT_PT_wireframetools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    
    def draw(self, context):
        

        wireColorTools = bpy.context.scene.wireColorTools
        
        layout = self.layout
        obj = context.object
  
        col = layout.column()
        colsplit = col.split()
        if len(bpy.context.scene.wireColorTools) > 0:
            colsplit.operator("wirecolorrandom.button")
            row = layout.row()
            rowsplit = row.split(factor = 0.5, align = True )

        
            rowsplit.operator("wirecolorset.button")
            rowsplit.prop(wireColorTools[0], "wireColSet", text="")
            
            row = layout.row()
            rowsplit = row.split(factor = 0.51, align = True )
            rowsplit.operator("wirecolorrandomrange.button")
            rowsplit.prop(wireColorTools[0], "wireColMin", text="")
            rowsplit.prop(wireColorTools[0], "wireColMax", text="")
            colsplit.operator("wirecolormaterial.button")

        else:
            row = layout.row()
            rowsplit = row.split(factor = 0.5, align = True )
            rowsplit.operator("wirecolorstart.button")



class WireColorRandomRange(bpy.types.Operator):
    bl_idname = "wirecolorrandomrange.button"
    bl_label = "Set Color Range"
       
    def execute(self, context):
        
        wireColorMin = bpy.context.scene.wireColorTools[0].wireColMin
        wireColorMax = bpy.context.scene.wireColorTools[0].wireColMax
        wireColorNew = bpy.context.scene.wireColorTools[0].wireColNew
        
        objects = bpy.context.selected_objects
        
        rangeV = getRange(wireColorMin.v, wireColorMax.v)
        if wireColorMin.v > wireColorMax.v:
            rangeV = rangeV * (-1)
        if wireColorMin.v == 0:
            wireColorMin.v = wireColorMax.v * 0.01
            wireColorMin.h = wireColorMax.h
        if wireColorMax.v == 0:
            wireColorMax.v = wireColorMin.v * 0.01            
            wireColorMax.h = wireColorMin.h

        rangeS = getRange(wireColorMin.s, wireColorMax.s)
        if wireColorMin.s > wireColorMax.s:
            rangeS = rangeS * (-1)
        if wireColorMin.s == 0:
            wireColorMin.s = wireColorMax.s * 0.01
            wireColorMin.h = wireColorMax.h
        if wireColorMax.s == 0:
            wireColorMax.s = wireColorMin.s * 0.01
            wireColorMax.h = wireColorMin.h

        rangeH = getRange(wireColorMin.h, wireColorMax.h)
        if wireColorMin.h < wireColorMax.h  and rangeH < 0.5:
            rangeH = rangeH
        elif wireColorMin.h > wireColorMax.h  and rangeH < 0.5:
            rangeH = rangeH * (-1)
        elif wireColorMin.h < wireColorMax.h  and rangeH > 0.5:
            rangeH = -1 + rangeH
        elif wireColorMin.h > wireColorMax.h  and rangeH > 0.5:
            rangeH = 1 - rangeH    
        
        for i in objects:
            
            wireColorNew[0] = wireColorMin[0]
            wireColorNew[1] = wireColorMin[1]
            wireColorNew[2] = wireColorMin[2]
                        
            random = numpy.random.rand(1,3)
                    
            wireColorNewHTemp = wireColorMin.h + (rangeH * random[0][0])
      
            if wireColorNewHTemp < 0:
                wireColorNewHTemp = 1 + wireColorNewHTemp
            elif wireColorNewHTemp > 1:
                wireColorNewHTemp = wireColorNewHTemp - 1
                
            wireColorNew.h = wireColorNewHTemp
            wireColorNew.s = wireColorMin.s + rangeS * random[0][1]
            wireColorNew.v = wireColorMin.v + rangeV * random[0][2]
            
            i.color = [wireColorNew[0], wireColorNew[1], wireColorNew[2], 1]
            
            

        return{'FINISHED'}


class WireColorRandomColor(bpy.types.Operator):
    bl_idname = "wirecolorrandom.button"
    bl_label = "Random Color"
    
    def execute(self, context):
        objects = bpy.context.selected_objects
        
        for i in objects:

            randomColor = numpy.random.rand(1,3)
            i.color = [randomColor[0][0],randomColor[0][1],randomColor[0][2],1]

        return{'FINISHED'}


class WireColorSet(bpy.types.Operator):
    bl_idname = "wirecolorset.button"
    bl_label = "Set Color"
    
    def execute(self, context):
        objects = bpy.context.selected_objects
        
        wireColorSet = bpy.context.scene.wireColorTools[0].wireColSet
        
        for i in objects:
        
            i.color = [wireColorSet[0],wireColorSet[1],wireColorSet[2],1]

        return{'FINISHED'}

class WireColorMaterial(bpy.types.Operator):
    bl_idname = "wirecolormaterial.button"
    bl_label = "Get from Material"
    
    def execute(self, context):
        
        objects = bpy.context.selected_objects
        for i in objects:
            if len(i.material_slots) > 0:
                i.color = i.material_slots[0].material.diffuse_color
                print(i.material_slots[0].material.diffuse_color)
            
        return{'FINISHED'}    

def getRange(From, To):
    range = max(From, To) - min(From, To)
    return(range)


class WireColorStart(bpy.types.Operator):
    bl_idname = "wirecolorstart.button"
    bl_label = "Open Wire Color"
    
    def execute(self, context):
        
        bpy.context.scene.wireColorTools.add()

        return{'FINISHED'}



classes = (
    WireFrameColorTools,
    WireColorSet,
    WireColorRandomColor,
    WireColorRandomRange,
    WireframeColorToolsPanel,
    WireColorMaterial,
    WireColorStart
    
)

def register():
    

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.wireColorTools = bpy.props.CollectionProperty(type=WireFrameColorTools)
    


def unregister():
    del bpy.types.Scene.wireColorTools
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    
if __name__ == "__main__":
    register()