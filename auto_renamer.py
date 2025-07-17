bl_info = {
    "name": "Auto High-Low Rename",
    "author": "Gwyn",
    "version": (1, 0, 2),
    "blender": (2, 80, 0),
    "location": "3D Viewport > Object > Auto High-Low Rename",
    "description": "Automatically renames selected meshes with _low and _high suffixes for Marmoset workflow",
    "category": "Object",
}

import bpy
import bmesh
import re
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import BoolProperty, PointerProperty

class AutoHighLowRenameProperties(PropertyGroup):
    """Properties for Auto High-Low Rename"""
    remove_existing_suffixes: BoolProperty(
        name="Remove Suffixes",
        description="Remove existing _low and _high suffixes before renaming",
        default=True
    )
    
    set_high_color: BoolProperty(
        name="Set HP Color",
        description="Set _high object color to blue (#9BC6FF) in Viewport Display",
        default=True
    )
    
    reset_low_color: BoolProperty(
        name="Reset LP Color",
        description="Reset _low object color to default (white)",
        default=True
    )

class OBJECT_OT_auto_high_low_rename(Operator):
    """Rename selected objects based on polygon count for Marmoset workflow"""
    bl_idname = "object.auto_high_low_rename"
    bl_label = "Auto High-Low Rename"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                len(context.selected_objects) == 2 and
                all(obj.type == 'MESH' for obj in context.selected_objects))
    
    def get_polygon_count(self, obj, context):
        """Get polygon count including modifiers"""
        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        
        if eval_obj.data.polygons:
            return len(eval_obj.data.polygons)
        else:
            bm = bmesh.new()
            bm.from_mesh(eval_obj.data)
            poly_count = len(bm.faces)
            bm.free()
            return poly_count
    
    def get_base_name(self, name):
        """Get base name by removing common suffixes and extensions"""
        # First remove Blender's automatic numeric suffixes (.001, .002, etc.)
        name = re.sub(r'\.\d+$', '', name)
        
        # Remove numeric prefixes (01_, 02_, etc.)
        name = re.sub(r'^\d+_', '', name)
        
        # Then remove _low and _high suffixes
        if name.endswith('_low'):
            name = name[:-4]
        elif name.endswith('_high'):
            name = name[:-5]
        
        # Remove any remaining Blender numeric suffixes that might be in the middle
        name = re.sub(r'\.\d+', '', name)
        
        return name
    
    def get_unique_names(self, base_name, selected_objects):
        """Get unique names with prefix if needed"""
        low_name = base_name + '_low'
        high_name = base_name + '_high'
        
        # Get names of all objects EXCEPT the currently selected ones
        selected_names = {obj.name for obj in selected_objects}
        existing_objects = [obj.name for obj in bpy.data.objects if obj.name not in selected_names]
        
        if low_name in existing_objects or high_name in existing_objects:
            # Find the next available counter by checking existing prefixed names
            counter = 1
            while True:
                prefix = f"{counter:02d}_"
                test_low = prefix + low_name
                test_high = prefix + high_name
                
                if test_low not in existing_objects and test_high not in existing_objects:
                    return test_low, test_high
                
                counter += 1
                
                if counter > 999:
                    break
        
        return low_name, high_name
    
    def execute(self, context):
        props = context.scene.auto_high_low_rename_props
        selected_objects = context.selected_objects
        
        if len(selected_objects) != 2:
            self.report({'ERROR'}, "Please select exactly 2 mesh objects")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in selected_objects if obj.type == 'MESH']
        if len(mesh_objects) != 2:
            self.report({'ERROR'}, "Both selected objects must be meshes")
            return {'CANCELLED'}
        
        poly_counts = []
        for obj in mesh_objects:
            poly_count = self.get_polygon_count(obj, context)
            poly_counts.append((obj, poly_count))
        
        poly_counts.sort(key=lambda x: x[1])
        low_poly_obj, low_count = poly_counts[0]
        high_poly_obj, high_count = poly_counts[1]
        
        base_name_1 = self.get_base_name(low_poly_obj.name) if props.remove_existing_suffixes else low_poly_obj.name
        base_name_2 = self.get_base_name(high_poly_obj.name) if props.remove_existing_suffixes else high_poly_obj.name
        
        if base_name_1 == base_name_2:
            base_name = base_name_1
        else:
            common_prefix = ""
            for i in range(min(len(base_name_1), len(base_name_2))):
                if base_name_1[i] == base_name_2[i]:
                    common_prefix += base_name_1[i]
                else:
                    break
            
            if len(common_prefix) > 3:
                base_name = common_prefix.rstrip('_')
            else:
                base_name = base_name_1
        
        if props.remove_existing_suffixes:
            final_low_name, final_high_name = self.get_unique_names(base_name, selected_objects)
            
            temp_low_name = "temp_low_" + str(id(low_poly_obj))
            temp_high_name = "temp_high_" + str(id(high_poly_obj))
            
            low_poly_obj.name = temp_low_name
            high_poly_obj.name = temp_high_name
            
            low_poly_obj.name = final_low_name
            high_poly_obj.name = final_high_name
        else:
            low_poly_obj.name = low_poly_obj.name + '_low'
            high_poly_obj.name = high_poly_obj.name + '_high'
        
        if props.set_high_color:
            high_poly_obj.color = (0.608, 0.776, 1.0, 1.0)
        
        if props.reset_low_color:
            low_poly_obj.color = (1.0, 1.0, 1.0, 1.0)
        
        self.report({'INFO'}, 
                   f"Renamed: {low_poly_obj.name} ({low_count} polys) and {high_poly_obj.name} ({high_count} polys)")
        
        return {'FINISHED'}

class OBJECT_OT_quick_select_pair(Operator):
    """Quick select the pair objects (_low/_high) for selected meshes"""
    bl_idname = "object.quick_select_pair"
    bl_label = "Quick Select Pair"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)
    
    def get_base_name(self, name):
        """Get base name by removing common suffixes and extensions (case insensitive)"""
        name_lower = name.lower()
        
        if name_lower.endswith('_low'):
            name = name[:-4]
        elif name_lower.endswith('_high'):
            name = name[:-5]
        
        return name
    
    def get_suffix_type(self, name):
        """Determine suffix type (low/high/none) - case insensitive"""
        name_lower = name.lower()
        
        if name_lower.endswith('_low'):
            return 'low'
        elif name_lower.endswith('_high'):
            return 'high'
        else:
            return 'none'
    
    def find_pair_object(self, obj_name):
        """Find the pair object for the given object name (case insensitive)"""
        suffix_type = self.get_suffix_type(obj_name)
        base_name = self.get_base_name(obj_name)

        # If it's just a numeric copy (Scope_frame.001, etc.), don't search for a pair
        if suffix_type == 'none' and re.search(r'\.\d+$', obj_name):
            return None

        # Function to compare base names (case-insensitive, ignoring prefixes)
        def base_names_match(name1, name2):
            clean1 = re.sub(r'^\d+_', '', name1).lower()
            clean2 = re.sub(r'^\d+_', '', name2).lower()
            return clean1 == clean2

        if suffix_type == 'low':
            target_suffixes = ['_high', '_High', '_HIGH']
            for suffix in target_suffixes:
                target_name = base_name + suffix
                if target_name in bpy.data.objects:
                    return bpy.data.objects[target_name]
            for obj in bpy.data.objects:
                if self.get_suffix_type(obj.name) == 'high':
                    obj_base = self.get_base_name(obj.name)
                    if base_names_match(obj_base, base_name):
                        return obj

        elif suffix_type == 'high':
            target_suffixes = ['_low', '_Low', '_LOW']
            for suffix in target_suffixes:
                target_name = base_name + suffix
                if target_name in bpy.data.objects:
                    return bpy.data.objects[target_name]
            for obj in bpy.data.objects:
                if self.get_suffix_type(obj.name) == 'low':
                    obj_base = self.get_base_name(obj.name)
                    if base_names_match(obj_base, base_name):
                        return obj

        else:
            clean_base_name = re.sub(r'\.\d+$', '', base_name)
            all_suffixes = ['_low', '_Low', '_LOW', '_high', '_High', '_HIGH']
            for suffix in all_suffixes:
                target_name = clean_base_name + suffix
                if target_name in bpy.data.objects:
                    return bpy.data.objects[target_name]

        return None
    
    def execute(self, context):
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_meshes:
            self.report({'ERROR'}, "Please select at least one mesh object")
            return {'CANCELLED'}
        
        pairs_found = []
        pairs_not_found = []
        objects_to_select = set()
        
        for obj in selected_meshes:
            objects_to_select.add(obj)
        
        for obj in selected_meshes:
            pair_obj = self.find_pair_object(obj.name)
            
            if pair_obj:
                pairs_found.append((obj.name, pair_obj.name))
                objects_to_select.add(pair_obj)
            else:
                pairs_not_found.append(obj.name)
        
        for obj in bpy.data.objects:
            obj.select_set(False)
        
        for obj in objects_to_select:
            obj.select_set(True)
        
        if pairs_found:
            last_pair_name = pairs_found[-1][1]
            if last_pair_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[last_pair_name]
        elif selected_meshes:
            context.view_layer.objects.active = selected_meshes[0]
        
        total_selected = len(selected_meshes)
        pairs_found_count = len(pairs_found)
        
        if pairs_found_count > 0:
            if pairs_not_found:
                self.report({'INFO'}, 
                           f"Found {pairs_found_count} pairs out of {total_selected} objects. "
                           f"No pairs found for: {', '.join(pairs_not_found)}")
            else:
                self.report({'INFO'}, 
                           f"Found all {pairs_found_count} pairs! "
                           f"Selected {len(objects_to_select)} objects total")
        else:
            self.report({'WARNING'}, 
                       f"No pairs found for any of the {total_selected} selected objects")
        
        return {'FINISHED'}

class VIEW3D_PT_auto_high_low_rename(Panel):
    """Panel for Auto High-Low Rename in 3D Viewport"""
    bl_label = "Auto High-Low Rename"
    bl_idname = "VIEW3D_PT_auto_high_low_rename"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.auto_high_low_rename_props
        
        box = layout.box()
        box.label(text="High-Low Tools:", icon='SORTALPHA')
        
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if len(selected_meshes) == 2:
            box.operator("object.auto_high_low_rename", text="Auto High-Low Rename")
        else:
            row = box.row()
            row.operator("object.auto_high_low_rename", text="Auto High-Low Rename")
            row.enabled = False
        
        if selected_meshes:
            box.operator("object.quick_select_pair", text="Select Pair", icon='LINKED')
        else:
            row = box.row()
            row.operator("object.quick_select_pair", text="Select Pair", icon='LINKED')
            row.enabled = False
        
        settings_box = layout.box()
        row = settings_box.row()
        row.prop(props, "set_high_color")
        row.prop(props, "remove_existing_suffixes")
        settings_box.prop(props, "reset_low_color")

# Updated: Function to add both buttons to editor menus (like SIMPLE TABS)
def draw_editor_menu_button(self, context):
    """Draw the Auto High-Low Rename and Select Pair buttons in the editor menus"""
    layout = self.layout
    selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
    
    # Auto High-Low Rename button
    if len(selected_meshes) == 2:
        layout.operator("object.auto_high_low_rename", text="", icon='SORTALPHA')
    else:
        row = layout.row()
        row.operator("object.auto_high_low_rename", text="", icon='SORTALPHA')
        row.enabled = False
    
    # Select Pair button
    if selected_meshes:
        layout.operator("object.quick_select_pair", text="", icon='LINKED')
    else:
        row = layout.row()
        row.operator("object.quick_select_pair", text="", icon='LINKED')
        row.enabled = False

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_auto_high_low_rename.bl_idname)

def menu_func_quick_select(self, context):
    self.layout.operator(OBJECT_OT_quick_select_pair.bl_idname)

def register():
    bpy.utils.register_class(AutoHighLowRenameProperties)
    bpy.utils.register_class(OBJECT_OT_auto_high_low_rename)
    bpy.utils.register_class(OBJECT_OT_quick_select_pair)
    bpy.utils.register_class(VIEW3D_PT_auto_high_low_rename)
    bpy.types.Scene.auto_high_low_rename_props = PointerProperty(type=AutoHighLowRenameProperties)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.types.VIEW3D_MT_object.append(menu_func_quick_select)
    
    # Register both buttons in editor menus
    bpy.types.VIEW3D_MT_editor_menus.append(draw_editor_menu_button)

def unregister():
    bpy.utils.unregister_class(AutoHighLowRenameProperties)
    bpy.utils.unregister_class(OBJECT_OT_auto_high_low_rename)
    bpy.utils.unregister_class(OBJECT_OT_quick_select_pair)
    bpy.utils.unregister_class(VIEW3D_PT_auto_high_low_rename)
    del bpy.types.Scene.auto_high_low_rename_props
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.types.VIEW3D_MT_object.remove(menu_func_quick_select)
    
    # Remove buttons from editor menus
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_editor_menu_button)

if __name__ == "__main__":
    register()