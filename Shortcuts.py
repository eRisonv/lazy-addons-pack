bl_info = {
    "name": "Shortcuts",
    "author": "Gwyn",
    "version": (1, 1, 0),
    "blender": (4, 0, 2),
    "location": "Object/Edit Mode",
    "description": "Adds hotkeys for selection modes, object mode, subdivision and wireframe toggle",
    "category": "3D View",
}

import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty

# Функция для переключения режима
def switch_to_edit_mode(mode):
    if bpy.context.active_object and bpy.context.active_object.type == 'MESH':
        if bpy.context.active_object.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type=mode)
        return True
    return False

# Операторы для режимов редактирования
class OBJECT_OT_switch_to_edge_mode(Operator):
    """Switch to Edit Mode (Edge Select)"""
    bl_idname = "object.switch_to_edge_mode"
    bl_label = "Switch to Edge Mode"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        if switch_to_edit_mode('EDGE'):
            return {'FINISHED'}
        self.report({'WARNING'}, "Select a mesh object first")
        return {'CANCELLED'}

class OBJECT_OT_switch_to_vertex_mode(Operator):
    """Switch to Edit Mode (Vertex Select)"""
    bl_idname = "object.switch_to_vertex_mode"
    bl_label = "Switch to Vertex Mode"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        if switch_to_edit_mode('VERT'):
            return {'FINISHED'}
        self.report({'WARNING'}, "Select a mesh object first")
        return {'CANCELLED'}

class OBJECT_OT_switch_to_face_mode(Operator):
    """Switch to Edit Mode (Face Select)"""
    bl_idname = "object.switch_to_face_mode"
    bl_label = "Switch to Face Mode"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        if switch_to_edit_mode('FACE'):
            return {'FINISHED'}
        self.report({'WARNING'}, "Select a mesh object first")
        return {'CANCELLED'}

class MESH_OT_switch_to_object_mode(Operator):
    """Switch to Object Mode"""
    bl_idname = "mesh.switch_to_object_mode"
    bl_label = "Switch to Object Mode"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class OBJECT_OT_subdivision_toggle(Operator):
    bl_idname = "object.subdivision_toggle"
    bl_label = "Toggle Subdivision"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        subsurf_mod = next((mod for mod in obj.modifiers if mod.type == 'SUBSURF'), None)

        if subsurf_mod:
            subsurf_mod.show_viewport = not subsurf_mod.show_viewport
        else:
            subsurf_mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            subsurf_mod.levels = 2

        return {'FINISHED'}

class VIEW3D_OT_toggle_wireframe(Operator):
    """Toggle between Wireframe and previous shading mode"""
    bl_idname = "view3d.toggle_wireframe"
    bl_label = "Toggle Wireframe"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Проверяем, что мы в контексте 3D-вида
        return any(area.type == 'VIEW_3D' for area in context.screen.areas)

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Получаем сцену для хранения предыдущего режима
                        scene = context.scene
                        
                        # Если свойство не существует, создаем его
                        if "previous_shading_mode" not in scene:
                            scene["previous_shading_mode"] = 'SOLID'
                        
                        current_mode = space.shading.type
                        
                        if current_mode == 'WIREFRAME':
                            # Возвращаемся к предыдущему режиму
                            space.shading.type = scene["previous_shading_mode"]
                        else:
                            # Сохраняем текущий режим и переключаемся на wireframe
                            scene["previous_shading_mode"] = current_mode
                            space.shading.type = 'WIREFRAME'
                        break
        return {'FINISHED'}

class ShortcutsPreferences(AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        kc = wm.keyconfigs.user

        if not kc:
            layout.label(text="User keyconfig not available")
            return

        keymap_entries = [
            {"operator": "object.switch_to_vertex_mode", "label": "Vertex Mode", "keymap_name": "Object Mode", "space_type": 'EMPTY'},
            {"operator": "object.switch_to_edge_mode", "label": "Edge Mode", "keymap_name": "Object Mode", "space_type": 'EMPTY'},
            {"operator": "object.switch_to_face_mode", "label": "Face Mode", "keymap_name": "Object Mode", "space_type": 'EMPTY'},
            {"operator": "mesh.switch_to_object_mode", "label": "Object Mode", "keymap_name": "Mesh", "space_type": 'EMPTY'},
            {"operator": "object.subdivision_toggle", "label": "Toggle Subdivision", "keymap_name": "3D View", "space_type": 'VIEW_3D'},
            {"operator": "view3d.toggle_wireframe", "label": "Toggle Wireframe", "keymap_name": "3D View", "space_type": 'VIEW_3D'},
        ]

        for entry in keymap_entries:
            operator_id = entry["operator"]
            label = entry["label"]
            keymap_name = entry["keymap_name"]
            space_type = entry["space_type"]

            kmi = None
            for km in kc.keymaps:
                if km.name == keymap_name and km.space_type == space_type:
                    for item in km.keymap_items:
                        if item.idname == operator_id:
                            kmi = item
                            break
                    if kmi:
                        break

            if not kmi:
                for km, item in addon_keymaps:
                    if km.name == keymap_name and km.space_type == space_type and item.idname == operator_id:
                        kmi = item
                        break

            if kmi:
                box = layout.box()
                row = box.row()
                row.label(text=label)
                row = box.row()
                row.prop(kmi, "type", text="Key", full_event=True)
            else:
                layout.label(text=f"{label}: Not bound")

# Регистрация горячих клавиш
addon_keymaps = []

def register_keymaps():
    unregister_keymaps()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    
    if not kc:
        print("Keyconfig not available!")
        return

    keymap_data = [
        ("3D View", 'VIEW_3D', [
            ("view3d.toggle_wireframe", 'W', {'ctrl': True, 'shift': True}),  # Изменено на Ctrl+Shift+W
            ("object.subdivision_toggle", 'SIX', {}),
        ]),
        ("Object Mode", 'EMPTY', [
            ("object.switch_to_vertex_mode", 'ONE', {'ctrl': True}),
            ("object.switch_to_edge_mode", 'TWO', {'ctrl': True}),
            ("object.switch_to_face_mode", 'THREE', {'ctrl': True}),
        ]),
        ("Mesh", 'EMPTY', [
            ("mesh.switch_to_object_mode", 'FOUR', {'ctrl': True}),
        ]),
    ]

    for km_name, space_type, items in keymap_data:
        km = kc.keymaps.new(name=km_name, space_type=space_type)
        for operator_id, key, modifiers in items:
            kmi = km.keymap_items.new(operator_id, key, 'PRESS', **modifiers)
            addon_keymaps.append((km, kmi))

classes = [
    OBJECT_OT_switch_to_edge_mode,
    OBJECT_OT_switch_to_vertex_mode,
    OBJECT_OT_switch_to_face_mode,
    MESH_OT_switch_to_object_mode,
    OBJECT_OT_subdivision_toggle,
    VIEW3D_OT_toggle_wireframe,
    ShortcutsPreferences,
]

def unregister_keymaps():
    for km, kmi in addon_keymaps:
        try:
            if km and kmi:
                km.keymap_items.remove(kmi)
        except Exception as e:
            print(f"Error removing keymap: {str(e)}")
    addon_keymaps.clear()

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymaps()
    bpy.app.handlers.load_post.append(reload_keymaps)

def reload_keymaps(dummy):
    register_keymaps()
    return None

def unregister():
    if reload_keymaps in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(reload_keymaps)
    unregister_keymaps()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()