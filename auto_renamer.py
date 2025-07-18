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
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import BoolProperty, PointerProperty, CollectionProperty, StringProperty

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
    
    def get_object_collection_path(self, obj):
        """Get collection path for an object"""
        collections = []
        
        # Get all collections containing this object
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                collections.append(collection)
        
        if not collections:
            return "Scene Collection"
        
        # Find the deepest collection hierarchy
        paths = []
        for collection in collections:
            path = self.get_collection_hierarchy(collection)
            paths.append(path)
        
        # Return the longest path (deepest hierarchy)
        if paths:
            return max(paths, key=len)
        else:
            return "Scene Collection"
    
    def get_collection_hierarchy(self, collection):
        """Get the full hierarchy path of a collection"""
        path = [collection.name]
        
        # Find parent collections
        for parent_collection in bpy.data.collections:
            if collection.name in parent_collection.children:
                parent_path = self.get_collection_hierarchy(parent_collection)
                return parent_path + "->" + "->".join(path)
        
        # Check if it's a child of the scene collection
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
        props = context.scene.auto_high_low_rename_props
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_meshes:
            self.report({'ERROR'}, "Please select at least one mesh object")
            return {'CANCELLED'}
        
        # Clear the previous list
        props.selected_objects_list.clear()
        
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
        
        # Функция для сортировки объектов по парам
        def sort_objects_by_pairs(objects_set):
            """Сортирует объекты по парам: сначала _low, потом _high"""
            objects_list = list(objects_set)
            paired_objects = []
            unpaired_objects = []
            processed_objects = set()
            
            for obj in objects_list:
                if obj in processed_objects:
                    continue
                    
                # Проверяем, есть ли пара для этого объекта
                pair_obj = self.find_pair_object(obj.name)
                
                if pair_obj and pair_obj in objects_set:
                    # Определяем, какой объект _low, а какой _high
                    obj_suffix = self.get_suffix_type(obj.name)
                    pair_suffix = self.get_suffix_type(pair_obj.name)
                    
                    if obj_suffix == 'low' and pair_suffix == 'high':
                        paired_objects.extend([obj, pair_obj])
                    elif obj_suffix == 'high' and pair_suffix == 'low':
                        paired_objects.extend([pair_obj, obj])
                    else:
                        # Если суффиксы неопределены, сортируем по алфавиту
                        if obj.name.lower() < pair_obj.name.lower():
                            paired_objects.extend([obj, pair_obj])
                        else:
                            paired_objects.extend([pair_obj, obj])
                    
                    processed_objects.add(obj)
                    processed_objects.add(pair_obj)
                else:
                    unpaired_objects.append(obj)
                    processed_objects.add(obj)
            
            # Сортируем непарные объекты по имени
            unpaired_objects.sort(key=lambda x: x.name.lower())
            
            return paired_objects + unpaired_objects
        
        # Сортируем объекты по парам
        sorted_objects = sort_objects_by_pairs(objects_to_select)
        
        # Add sorted objects to the list with their collection paths
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
            
            # Переключаем видимость объекта
            is_currently_hidden = obj.hide_viewport or obj.hide_get()
            
            if is_currently_hidden:
                # Показываем объект
                obj.hide_viewport = False
                obj.hide_set(False)
                status = "visible"
            else:
                # Скрываем объект
                obj.hide_viewport = True
                obj.hide_set(True)
                status = "hidden"
            
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
            
            # Снимаем выделение со всех объектов
            for o in bpy.data.objects:
                o.select_set(False)
            
            # Выделяем нужный объект
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            # Если объект скрыт, показываем его
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
            
            # Получаем все коллекции объекта
            object_collections = []
            for collection in bpy.data.collections:
                if obj.name in collection.objects:
                    object_collections.append(collection)
            
            # Если объект в Scene Collection
            if obj.name in bpy.context.scene.collection.objects:
                object_collections.append(bpy.context.scene.collection)
            
            if not object_collections:
                self.report({'ERROR'}, f"Object '{self.object_name}' is not in any collection")
                return {'CANCELLED'}
            
            # Находим самую глубокую (вложенную) коллекцию
            deepest_collection = self.find_deepest_collection(object_collections)
            
            # Находим соответствующую layer_collection и получаем весь путь
            layer_col, path = self.find_layer_collection_with_path(deepest_collection)
            
            if layer_col and path:
                # Ищем первую скрытую коллекцию в пути (от корня к самой глубокой)
                hidden_collection = None
                for layer_collection in path:
                    if layer_collection.hide_viewport:
                        hidden_collection = layer_collection
                        break
                
                if hidden_collection:
                    # Если есть скрытая коллекция в пути, показываем её
                    hidden_collection.hide_viewport = False
                    status = f"Showed collection '{hidden_collection.collection.name}'"
                else:
                    # Если все коллекции в пути видимы, скрываем самую глубокую
                    layer_col.hide_viewport = True
                    status = f"Hidden collection '{layer_col.collection.name}'"
                    
                self.report({'INFO'}, status)
            else:
                self.report({'ERROR'}, f"Layer collection for '{deepest_collection.name}' not found")
        else:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
        
        return {'FINISHED'}


    def find_layer_collection_with_path(self, collection):
        """Найти layer_collection для данной коллекции и вернуть путь"""
        def find_layer_collection_recursive(layer_collection, collection_name, path=[]):
            current_path = path + [layer_collection]
            
            if layer_collection.collection.name == collection_name:
                return layer_collection, current_path
            
            for child in layer_collection.children:
                result, result_path = find_layer_collection_recursive(child, collection_name, current_path)
                if result:
                    return result, result_path
            
            return None, []
        
        view_layer = bpy.context.view_layer
        root_layer_collection = view_layer.layer_collection
        
        # Проверяем, не является ли это Scene Collection
        if collection == bpy.context.scene.collection:
            return root_layer_collection, [root_layer_collection]
        
        return find_layer_collection_recursive(root_layer_collection, collection.name)
    
    def find_deepest_collection(self, collections):
        """Найти самую глубокую (вложенную) коллекцию"""
        if not collections:
            return None
        
        # Если только одна коллекция, возвращаем её
        if len(collections) == 1:
            return collections[0]
        
        # Находим самую глубокую коллекцию по иерархии
        deepest = collections[0]
        max_depth = self.get_collection_depth(deepest)
        
        for collection in collections[1:]:
            depth = self.get_collection_depth(collection)
            if depth > max_depth:
                max_depth = depth
                deepest = collection
        
        return deepest
    
    def get_collection_depth(self, collection):
        """Получить глубину вложенности коллекции"""
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
                # Проверяем, является ли родителем Scene Collection
                if current.name in bpy.context.scene.collection.children:
                    depth += 1
                break
        
        return depth
    
    def find_layer_collection(self, collection):
        """Найти layer_collection для данной коллекции"""
        def find_layer_collection_recursive(layer_collection, collection_name):
            if layer_collection.collection.name == collection_name:
                return layer_collection
            
            for child in layer_collection.children:
                result = find_layer_collection_recursive(child, collection_name)
                if result:
                    return result
            
            return None
        
        view_layer = bpy.context.view_layer
        root_layer_collection = view_layer.layer_collection
        
        # Проверяем, не является ли это Scene Collection
        if collection == bpy.context.scene.collection:
            return root_layer_collection
        
        return find_layer_collection_recursive(root_layer_collection, collection.name)

def is_object_in_hidden_collection(obj):
    """Проверяет, находится ли объект в скрытой коллекции"""
    def find_layer_collection_with_path(layer_collection, collection_name, path=[]):
        """Рекурсивно находит layer_collection по имени и возвращает путь"""
        current_path = path + [layer_collection]
        
        if layer_collection.collection.name == collection_name:
            return layer_collection, current_path
        
        for child in layer_collection.children:
            result, result_path = find_layer_collection_with_path(child, collection_name, current_path)
            if result:
                return result, result_path
        
        return None, []
    
    def is_layer_collection_or_parents_hidden(layer_collection, path):
        """Проверяет, скрыта ли layer_collection или её родители"""
        # Проверяем текущую layer_collection
        if layer_collection.hide_viewport:
            return True
        
        # Проверяем родительские layer_collections по пути
        for parent_layer_col in path[:-1]:  # Исключаем саму коллекцию
            if parent_layer_col.hide_viewport:
                return True
        
        return False
    
    # Получаем корневую layer_collection
    view_layer = bpy.context.view_layer
    root_layer_collection = view_layer.layer_collection
    
    # Проверяем все коллекции, содержащие объект
    for collection in bpy.data.collections:
        if obj.name in collection.objects:
            # Находим соответствующую layer_collection с путём
            layer_col, path = find_layer_collection_with_path(root_layer_collection, collection.name)
            if layer_col and is_layer_collection_or_parents_hidden(layer_col, path):
                return True
    
    # Проверяем объекты в Scene Collection
    if obj.name in bpy.context.scene.collection.objects:
        if root_layer_collection.hide_viewport:
            return True
    
    return False

def is_object_in_scene_collection(obj):
    """Проверяет, находится ли объект только в Scene Collection"""
    # Проверяем, есть ли объект в Scene Collection
    if obj.name not in bpy.context.scene.collection.objects:
        return False
    
    # Проверяем, есть ли объект в других коллекциях
    for collection in bpy.data.collections:
        if obj.name in collection.objects:
            return False
    
    return True

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
        
        # Selected Objects List
        if props.selected_objects_list:
            list_box = layout.box()
            row = list_box.row()
            row.label(text="Selected Objects:", icon='VIEWZOOM')
            row.operator("object.clear_selected_list", text="Clear", icon='X')

            for item in props.selected_objects_list:
                row = list_box.row()
                
                # Get object to check visibility
                obj = bpy.data.objects.get(item.name)
                if obj:
                    # Проверяем состояния видимости
                    is_object_hidden = obj.hide_viewport or obj.hide_get()
                    is_in_hidden_collection = is_object_in_hidden_collection(obj)
                    is_in_scene_collection = is_object_in_scene_collection(obj)
                    
                    # ПЕРВАЯ КНОПКА: Видимость коллекции (показываем только если объект НЕ в Scene Collection)
                    if not is_in_scene_collection:
                        if is_in_hidden_collection:
                            collection_icon = 'COLLECTION_COLOR_08'  # Скрытая коллекция - оранжевый
                        else:
                            collection_icon = 'OUTLINER_COLLECTION'  # Видимая коллекция - обычная иконка
                        
                        toggle_collection_op = row.operator("object.toggle_collection_visibility", 
                                                           text="", icon=collection_icon)
                        toggle_collection_op.object_name = item.name
                    else:
                        # Если объект в Scene Collection, добавляем пустое место для выравнивания
                        row.label(text="", icon='BLANK1')
                    
                    # ВТОРАЯ КНОПКА: Видимость объекта
                    if is_object_hidden:
                        object_icon = 'HIDE_ON'  # Скрытый объект
                    else:
                        object_icon = 'HIDE_OFF'  # Видимый объект
                    
                    toggle_object_op = row.operator("object.toggle_object_visibility", 
                                                   text="", icon=object_icon)
                    toggle_object_op.object_name = item.name
                    
                    # ТРЕТЬЯ КНОПКА: Выделение объекта
                    select_op = row.operator("object.select_object", 
                                            text="", icon='RESTRICT_SELECT_OFF')
                    select_op.object_name = item.name
                    
                    # Object name and collection path
                    row.label(text=f"{item.name} [{item.collection_path}]", icon='MESH_DATA')
                else:
                    # Object not found, show warning
                    row.label(text="", icon='ERROR')
                    row.label(text="", icon='ERROR')
                    row.label(text="", icon='ERROR')
                    row.label(text=f"{item.name} [NOT FOUND]", icon='MESH_DATA')
        
        settings_box = layout.box()
        row = settings_box.row()
        row.prop(props, "set_high_color")
        row.prop(props, "remove_existing_suffixes")
        settings_box.prop(props, "reset_low_color")

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
    
    # Select Pair button - Changed icon to selection cursor
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
    bpy.utils.register_class(OBJECT_OT_auto_high_low_rename)
    bpy.utils.register_class(OBJECT_OT_quick_select_pair)
    bpy.utils.register_class(OBJECT_OT_clear_selected_list)
    bpy.utils.register_class(OBJECT_OT_toggle_object_visibility)
    bpy.utils.register_class(OBJECT_OT_toggle_collection_visibility)
    bpy.utils.register_class(OBJECT_OT_select_object)  # Добавляем новый оператор
    bpy.utils.register_class(VIEW3D_PT_auto_high_low_rename)
    bpy.types.Scene.auto_high_low_rename_props = PointerProperty(type=AutoHighLowRenameProperties)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.types.VIEW3D_MT_object.append(menu_func_quick_select)
    
    # Register both buttons in editor menus
    bpy.types.VIEW3D_MT_editor_menus.append(draw_editor_menu_button)
    
def unregister():
    bpy.utils.unregister_class(SelectedObjectItem)
    bpy.utils.unregister_class(AutoHighLowRenameProperties)
    bpy.utils.unregister_class(OBJECT_OT_auto_high_low_rename)
    bpy.utils.unregister_class(OBJECT_OT_quick_select_pair)
    bpy.utils.unregister_class(OBJECT_OT_clear_selected_list)
    bpy.utils.unregister_class(OBJECT_OT_toggle_object_visibility)
    bpy.utils.unregister_class(OBJECT_OT_toggle_collection_visibility)
    bpy.utils.unregister_class(OBJECT_OT_select_object)  # Удаляем новый оператор
    bpy.utils.unregister_class(VIEW3D_PT_auto_high_low_rename)
    del bpy.types.Scene.auto_high_low_rename_props
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.types.VIEW3D_MT_object.remove(menu_func_quick_select)
    
    # Remove buttons from editor menus
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_editor_menu_button)

if __name__ == "__main__":
    register()