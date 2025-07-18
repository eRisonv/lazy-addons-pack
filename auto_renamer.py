bl_info = {
    "name": "Auto High-Low Rename",
    "author": "Gwyn",
    "version": (1, 0, 3),
    "blender": (2, 80, 0),
    "location": "3D Viewport > Object > Auto High-Low Rename",
    "description": "Automatically renames selected meshes with _low and _high suffixes for Marmoset workflow",
    "category": "Object",
}

import bpy
import bmesh
import re
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy.props import BoolProperty, PointerProperty, CollectionProperty, StringProperty, IntProperty

class SelectedObjectItem(PropertyGroup):
    """Property group for storing selected object info"""
    name: StringProperty()
    collection_path: StringProperty()

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
    
    selected_objects_list: CollectionProperty(type=SelectedObjectItem)
    selected_objects_index: IntProperty()  # Добавлено для UIList

class SelectedObjectsListUIList(UIList):
    """Custom UIList for displaying selected objects with scrollbar"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            obj = bpy.data.objects.get(item.name)
            if obj:
                # ПЕРВАЯ КНОПКА: Видимость коллекции
                if not is_object_in_scene_collection(obj):
                    if is_object_in_hidden_collection(obj):
                        collection_icon = 'COLLECTION_COLOR_08'
                    else:
                        collection_icon = 'OUTLINER_COLLECTION'
                    toggle_collection_op = row.operator("object.toggle_collection_visibility", text="", icon=collection_icon)
                    toggle_collection_op.object_name = item.name
                else:
                    row.label(text="", icon='BLANK1')
                
                # ВТОРАЯ КНОПКА: Видимость объекта
                if obj.hide_viewport or obj.hide_get():
                    object_icon = 'HIDE_ON'
                else:
                    object_icon = 'HIDE_OFF'
                toggle_object_op = row.operator("object.toggle_object_visibility", text="", icon=object_icon)
                toggle_object_op.object_name = item.name
                
                # ТРЕТЬЯ КНОПКА: Выделение объекта
                select_op = row.operator("object.select_object", text="", icon='RESTRICT_SELECT_OFF')
                select_op.object_name = item.name
                
                # Object name and collection path
                row.label(text=f"{item.name} [{item.collection_path}]", icon='MESH_DATA')
            else:
                row.label(text="", icon='ERROR')
                row.label(text="", icon='ERROR')
                row.label(text="", icon='ERROR')
                row.label(text=f"{item.name} [NOT FOUND]", icon='MESH_DATA')

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
        name = re.sub(r'\.\d+$', '', name)
        name = re.sub(r'^\d+_', '', name)
        if name.endswith('_low'):
            name = name[:-4]
        elif name.endswith('_high'):
            name = name[:-5]
        name = re.sub(r'\.\d+', '', name)
        return name
    
    def get_unique_names(self, base_name, selected_objects):
        """Get unique names with prefix if needed"""
        low_name = base_name + '_low'
        high_name = base_name + '_high'
        selected_names = {obj.name for obj in selected_objects}
        existing_objects = [obj.name for obj in bpy.data.objects if obj.name not in selected_names]
        
        if low_name in existing_objects or high_name in existing_objects:
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
    
    def get_object_collection_path(self, obj):
        """Get collection path for an object"""
        collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                collections.append(collection)
        if not collections:
            return "Scene Collection"
        paths = []
        for collection in collections:
            path = self.get_collection_hierarchy(collection)
            paths.append(path)
        return max(paths, key=len) if paths else "Scene Collection"
    
    def get_collection_hierarchy(self, collection):
        """Get the full hierarchy path of a collection"""
        path = [collection.name]
        for parent_collection in bpy.data.collections:
            if collection.name in parent_collection.children:
                parent_path = self.get_collection_hierarchy(parent_collection)
                return parent_path + "->" + "->".join(path)
        if collection.name in bpy.context.scene.collection.children:
            return "->".join(path)
        return "->".join(path)
    
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
        if suffix_type == 'none' and re.search(r'\.\d+$', obj_name):
            return None
        
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
                if self.get_suffix_type(obj.name) == 'high' and base_names_match(self.get_base_name(obj.name), base_name):
                    return obj
        elif suffix_type == 'high':
            target_suffixes = ['_low', '_Low', '_LOW']
            for suffix in target_suffixes:
                target_name = base_name + suffix
                if target_name in bpy.data.objects:
                    return bpy.data.objects[target_name]
            for obj in bpy.data.objects:
                if self.get_suffix_type(obj.name) == 'low' and base_names_match(self.get_base_name(obj.name), base_name):
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
        props = context.scene.auto_high_low_rename_props
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_meshes:
            self.report({'ERROR'}, "Please select at least one mesh object")
            return {'CANCELLED'}
        
        props.selected_objects_list.clear()
        pairs_found = []
        pairs_not_found = []
        objects_to_select = set(selected_meshes)
        
        for obj in selected_meshes:
            pair_obj = self.find_pair_object(obj.name)
            if pair_obj:
                pairs_found.append((obj.name, pair_obj.name))
                objects_to_select.add(pair_obj)
            else:
                pairs_not_found.append(obj.name)
        
        def sort_objects_by_pairs(objects_set):
            """Sort objects by pairs: _low first, then _high"""
            objects_list = list(objects_set)
            paired_objects = []
            unpaired_objects = []
            processed_objects = set()
            for obj in objects_list:
                if obj in processed_objects:
                    continue
                pair_obj = self.find_pair_object(obj.name)
                if pair_obj and pair_obj in objects_set:
                    obj_suffix = self.get_suffix_type(obj.name)
                    pair_suffix = self.get_suffix_type(pair_obj.name)
                    if obj_suffix == 'low' and pair_suffix == 'high':
                        paired_objects.extend([obj, pair_obj])
                    elif obj_suffix == 'high' and pair_suffix == 'low':
                        paired_objects.extend([pair_obj, obj])
                    else:
                        paired_objects.extend(sorted([obj, pair_obj], key=lambda x: x.name.lower()))
                    processed_objects.add(obj)
                    processed_objects.add(pair_obj)
                else:
                    unpaired_objects.append(obj)
                    processed_objects.add(obj)
            unpaired_objects.sort(key=lambda x: x.name.lower())
            return paired_objects + unpaired_objects
        
        sorted_objects = sort_objects_by_pairs(objects_to_select)
        for obj in sorted_objects:
            item = props.selected_objects_list.add()
            item.name = obj.name
            item.collection_path = self.get_object_collection_path(obj)
        
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

class OBJECT_OT_clear_selected_list(Operator):
    """Clear the selected objects list"""
    bl_idname = "object.clear_selected_list"
    bl_label = "Clear List"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.auto_high_low_rename_props
        props.selected_objects_list.clear()
        self.report({'INFO'}, "Selected objects list cleared")
        return {'FINISHED'}

class OBJECT_OT_toggle_object_visibility(Operator):
    """Toggle object visibility in viewport"""
    bl_idname = "object.toggle_object_visibility"
    bl_label = "Toggle Object Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    
    object_name: StringProperty()
    
    def execute(self, context):
        if self.object_name in bpy.data.objects:
            obj = bpy.data.objects[self.object_name]
            is_currently_hidden = obj.hide_viewport or obj.hide_get()
            if is_currently_hidden:
                obj.hide_viewport = False
                obj.hide_set(False)
            else:
                obj.hide_viewport = True
                obj.hide_set(True)
        else:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
        return {'FINISHED'}

class OBJECT_OT_select_object(Operator):
    """Select object in viewport"""
    bl_idname = "object.select_object"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'UNDO'}
    
    object_name: StringProperty()
    
    def execute(self, context):
        if self.object_name in bpy.data.objects:
            obj = bpy.data.objects[self.object_name]
            for o in bpy.data.objects:
                o.select_set(False)
            obj.select_set(True)
            context.view_layer.objects.active = obj
            if obj.hide_viewport or obj.hide_get():
                obj.hide_viewport = False
                obj.hide_set(False)
                self.report({'INFO'}, f"Selected and shown object '{obj.name}'")
            else:
                self.report({'INFO'}, f"Selected object '{obj.name}'")
        else:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
        return {'FINISHED'}

class OBJECT_OT_toggle_collection_visibility(Operator):
    """Toggle collection visibility in viewport"""
    bl_idname = "object.toggle_collection_visibility"
    bl_label = "Toggle Collection Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    
    object_name: StringProperty()
    
    def execute(self, context):
        if self.object_name in bpy.data.objects:
            obj = bpy.data.objects[self.object_name]
            object_collections = [col for col in bpy.data.collections if obj.name in col.objects]
            if obj.name in bpy.context.scene.collection.objects:
                object_collections.append(bpy.context.scene.collection)
            if not object_collections:
                self.report({'ERROR'}, f"Object '{self.object_name}' is not in any collection")
                return {'CANCELLED'}
            
            deepest_collection = self.find_deepest_collection(object_collections)
            layer_col, path = self.find_layer_collection_with_path(deepest_collection)
            if layer_col and path:
                hidden_collection = next((lc for lc in path if lc.hide_viewport), None)
                if hidden_collection:
                    hidden_collection.hide_viewport = False
                    self.report({'INFO'}, f"Showed collection '{hidden_collection.collection.name}'")
                else:
                    layer_col.hide_viewport = True
                    self.report({'INFO'}, f"Hidden collection '{layer_col.collection.name}'")
            else:
                self.report({'ERROR'}, f"Layer collection for '{deepest_collection.name}' not found")
        else:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
        return {'FINISHED'}
    
    def find_layer_collection_with_path(self, collection):
        """Find layer_collection for given collection and return path"""
        def find_recursive(layer_collection, collection_name, path=[]):
            current_path = path + [layer_collection]
            if layer_collection.collection.name == collection_name:
                return layer_collection, current_path
            for child in layer_collection.children:
                result, result_path = find_recursive(child, collection_name, current_path)
                if result:
                    return result, result_path
            return None, []
        
        view_layer = bpy.context.view_layer
        root_layer_collection = view_layer.layer_collection
        if collection == bpy.context.scene.collection:
            return root_layer_collection, [root_layer_collection]
        return find_recursive(root_layer_collection, collection.name)
    
    def find_deepest_collection(self, collections):
        """Find the deepest nested collection"""
        if not collections:
            return None
        if len(collections) == 1:
            return collections[0]
        deepest = collections[0]
        max_depth = self.get_collection_depth(deepest)
        for collection in collections[1:]:
            depth = self.get_collection_depth(collection)
            if depth > max_depth:
                max_depth = depth
                deepest = collection
        return deepest
    
    def get_collection_depth(self, collection):
        """Get nesting depth of a collection"""
        if collection == bpy.context.scene.collection:
            return 0
        depth = 0
        current = collection
        while True:
            parent_found = False
            for parent_collection in bpy.data.collections:
                if current.name in parent_collection.children:
                    depth += 1
                    current = parent_collection
                    parent_found = True
                    break
            if not parent_found:
                if current.name in bpy.context.scene.collection.children:
                    depth += 1
                break
        return depth

def is_object_in_hidden_collection(obj):
    """Check if object is in a hidden collection"""
    def find_layer_collection_with_path(layer_collection, collection_name, path=[]):
        current_path = path + [layer_collection]
        if layer_collection.collection.name == collection_name:
            return layer_collection, current_path
        for child in layer_collection.children:
            result, result_path = find_layer_collection_with_path(child, collection_name, current_path)
            if result:
                return result, result_path
        return None, []
    
    def is_layer_collection_or_parents_hidden(layer_collection, path):
        if layer_collection.hide_viewport:
            return True
        return any(parent.hide_viewport for parent in path[:-1])
    
    view_layer = bpy.context.view_layer
    root_layer_collection = view_layer.layer_collection
    for collection in bpy.data.collections:
        if obj.name in collection.objects:
            layer_col, path = find_layer_collection_with_path(root_layer_collection, collection.name)
            if layer_col and is_layer_collection_or_parents_hidden(layer_col, path):
                return True
    if obj.name in bpy.context.scene.collection.objects and root_layer_collection.hide_viewport:
        return True
    return False

def is_object_in_scene_collection(obj):
    """Check if object is only in Scene Collection"""
    if obj.name not in bpy.context.scene.collection.objects:
        return False
    return not any(obj.name in col.objects for col in bpy.data.collections)

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
        
        # Selected Objects List with Scrollbar
        if props.selected_objects_list:
            list_box = layout.box()
            row = list_box.row()
            row.label(text="Selected Objects:", icon='VIEWZOOM')
            row.operator("object.clear_selected_list", text="Clear", icon='X')
            row = list_box.row()
            row.template_list("SelectedObjectsListUIList", "", props, "selected_objects_list", 
                            props, "selected_objects_index", rows=10)  # Ограничение на 10 строк
        
        settings_box = layout.box()
        row = settings_box.row()
        row.prop(props, "set_high_color")
        row.prop(props, "remove_existing_suffixes")
        settings_box.prop(props, "reset_low_color")

def draw_editor_menu_button(self, context):
    """Draw the Auto High-Low Rename and Select Pair buttons in the editor menus"""
    layout = self.layout
    selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if len(selected_meshes) == 2:
        layout.operator("object.auto_high_low_rename", text="", icon='SORTALPHA')
    else:
        row = layout.row()
        row.operator("object.auto_high_low_rename", text="", icon='SORTALPHA')
        row.enabled = False
    if selected_meshes:
        layout.operator("object.quick_select_pair", text="", icon='RESTRICT_SELECT_OFF')
    else:
        row = layout.row()
        row.operator("object.quick_select_pair", text="", icon='RESTRICT_SELECT_OFF')
        row.enabled = False

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_auto_high_low_rename.bl_idname)

def menu_func_quick_select(self, context):
    self.layout.operator(OBJECT_OT_quick_select_pair.bl_idname)

def register():
    bpy.utils.register_class(SelectedObjectItem)
    bpy.utils.register_class(AutoHighLowRenameProperties)
    bpy.utils.register_class(SelectedObjectsListUIList)  # Регистрация UIList
    bpy.utils.register_class(OBJECT_OT_auto_high_low_rename)
    bpy.utils.register_class(OBJECT_OT_quick_select_pair)
    bpy.utils.register_class(OBJECT_OT_clear_selected_list)
    bpy.utils.register_class(OBJECT_OT_toggle_object_visibility)
    bpy.utils.register_class(OBJECT_OT_toggle_collection_visibility)
    bpy.utils.register_class(OBJECT_OT_select_object)
    bpy.utils.register_class(VIEW3D_PT_auto_high_low_rename)
    bpy.types.Scene.auto_high_low_rename_props = PointerProperty(type=AutoHighLowRenameProperties)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.types.VIEW3D_MT_object.append(menu_func_quick_select)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_editor_menu_button)

def unregister():
    bpy.utils.unregister_class(SelectedObjectItem)
    bpy.utils.unregister_class(AutoHighLowRenameProperties)
    bpy.utils.unregister_class(SelectedObjectsListUIList)  # Удаление UIList
    bpy.utils.unregister_class(OBJECT_OT_auto_high_low_rename)
    bpy.utils.unregister_class(OBJECT_OT_quick_select_pair)
    bpy.utils.unregister_class(OBJECT_OT_clear_selected_list)
    bpy.utils.unregister_class(OBJECT_OT_toggle_object_visibility)
    bpy.utils.unregister_class(OBJECT_OT_toggle_collection_visibility)
    bpy.utils.unregister_class(OBJECT_OT_select_object)
    bpy.utils.unregister_class(VIEW3D_PT_auto_high_low_rename)
    del bpy.types.Scene.auto_high_low_rename_props
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.types.VIEW3D_MT_object.remove(menu_func_quick_select)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_editor_menu_button)

if __name__ == "__main__":
    register()