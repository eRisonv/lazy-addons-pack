bl_info = {
    "name": "My Tools",
    "author": "Gwyn",
    "version": (1, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Item tab, UV Editor > Sidebar > Tool tab",
    "description": ("Набор инструментов: выбор ребер с crease, выбор объектов с неравномерным масштабом, "
                    "настройка единиц измерения длины, Straight UV Square, работа с Bevel Weight"),
    "category": "3D View",
}

import bpy
import bmesh

# Оператор: Выбор ребер с crease больше порога и установка их в 1
class MESH_OT_select_crease_edges(bpy.types.Operator):
    bl_idname = "mesh.select_crease_edges"
    bl_label = "Select Crease Edges"
    bl_description = "Выбирает ребра с crease больше заданного порога и устанавливает его в 1"
    bl_options = {'REGISTER', 'UNDO'}

    threshold: bpy.props.FloatProperty(
        name="Threshold",
        description="Пороговое значение для crease",
        default=0.1,
        min=0.0,
        max=1.0,
    )

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        crease_attr = mesh.attributes.get("crease_edge")
        if crease_attr is None:
            self.report({'ERROR'}, "Атрибут crease_edge не найден в меш-данных")
            return {'CANCELLED'}

        crease_layer = bm.edges.layers.float.get(crease_attr.name)
        if crease_layer is None:
            self.report({'ERROR'}, "Слой данных для crease_edge не найден в BMesh")
            return {'CANCELLED'}

        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        for edge in bm.edges:
            if edge[crease_layer] > self.threshold:
                edge.select = True

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Установка Crease в 1 для выделенных рёбер
class MESH_OT_set_crease_one(bpy.types.Operator):
    bl_idname = "mesh.set_crease_one"
    bl_label = "Crease 1"
    bl_description = "Устанавливает Crease в 1 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой crease
        crease_layer = bm.edges.layers.float.get("crease_edge")
        if crease_layer is None:
            crease_layer = bm.edges.layers.float.new("crease_edge")

        bpy.ops.mesh.select_mode(type='EDGE')
        
        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[crease_layer] = 1.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Установка Crease в 0 для выделенных рёбер
class MESH_OT_set_crease_zero(bpy.types.Operator):
    bl_idname = "mesh.set_crease_zero"
    bl_label = "Crease 0"
    bl_description = "Устанавливает Crease в 0 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой crease
        crease_layer = bm.edges.layers.float.get("crease_edge")
        if crease_layer is None:
            crease_layer = bm.edges.layers.float.new("crease_edge")

        bpy.ops.mesh.select_mode(type='EDGE')
        
        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[crease_layer] = 0.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Установка Bevel Weight в 1 для выделенных рёбер
class MESH_OT_set_bevel_weight_one(bpy.types.Operator):
    bl_idname = "mesh.set_bevel_weight_one"
    bl_label = "Bevel Weight 1"
    bl_description = "Устанавливает Bevel Weight в 1 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой bevel_weight
        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            bevel_weight_layer = bm.edges.layers.float.new("bevel_weight_edge")

        bpy.ops.mesh.select_mode(type='EDGE')
        
        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[bevel_weight_layer] = 1.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Установка Bevel Weight в 0 для выделенных рёбер
class MESH_OT_set_bevel_weight_zero(bpy.types.Operator):
    bl_idname = "mesh.set_bevel_weight_zero"
    bl_label = "Bevel Weight 0"
    bl_description = "Устанавливает Bevel Weight в 0 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой bevel_weight
        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            bevel_weight_layer = bm.edges.layers.float.new("bevel_weight_edge")

        bpy.ops.mesh.select_mode(type='EDGE')
        
        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[bevel_weight_layer] = 0.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Выбор рёбер с Bevel Weight больше 0
class MESH_OT_select_bevel_weight_edges(bpy.types.Operator):
    bl_idname = "mesh.select_bevel_weight_edges"
    bl_label = "Select Bevel Weight Edges"
    bl_description = "Выбирает рёбра с Bevel Weight больше 0"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            self.report({'WARNING'}, "Bevel Weight слой не найден")
            return {'CANCELLED'}

        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        selected_count = 0
        for edge in bm.edges:
            if edge[bevel_weight_layer] > 0.0:
                edge.select = True
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Выбор острых рёбер (Mark Sharp)
class MESH_OT_select_sharp_edges(bpy.types.Operator):
    bl_idname = "mesh.select_sharp_edges"
    bl_label = "Select Sharp Edges"
    bl_description = "Выбирает рёбра помеченные как Sharp (Mark Sharp)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        selected_count = 0
        for edge in bm.edges:
            if not edge.smooth:  # edge.smooth = False означает Sharp
                edge.select = True
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}

# Оператор: Выбор объектов с неравномерным масштабом
class OBJECT_OT_select_non_uniform_scale(bpy.types.Operator):
    bl_idname = "object.select_non_uniform_scale"
    bl_label = "Select Scaled Objects"
    bl_description = "Выбирает объекты с неравномерным масштабом"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.view_layer.objects:
            obj.select_set(False)
        
        selected_count = 0
        for obj in context.view_layer.objects:
            if obj.type == 'MESH':
                if any(round(s, 6) != 1.0 for s in obj.scale):
                    obj.select_set(True)
                    selected_count += 1
        
        self.report({'INFO'}, f"Selected {selected_count} objects")
        return {'FINISHED'}

# Новый оператор: Выполнение последовательности UV операций (Straight UV Island)
class UV_OT_straight_uv_island(bpy.types.Operator):
    bl_idname = "uv.straight_uv_island"
    bl_label = "Straight UV Square"
    bl_description = ("Straighten UV square with mode selection")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        # Получаем контекст UV Editor
        uv_override = self.get_uv_context(context)
        if not uv_override:
            self.report({'ERROR'}, "UV Editor not found")
            return {'CANCELLED'}

        # Шаг 1: UV Squares by Shape
        with context.temp_override(**uv_override):
            bpy.ops.uv.uv_squares_by_shape()

        # Шаг 2: Select Linked
        with context.temp_override(**uv_override):
            bpy.ops.uv.select_linked()

        # Шаг 3: Follow Active Quads с выбором режима
        with context.temp_override(**uv_override):
            bpy.ops.uv.follow_active_quads('INVOKE_DEFAULT')

        # Возвращаем FINISHED, чтобы не запускать лишнее обновление выделения
        return {'FINISHED'}

    def get_uv_context(self, context):
        # Находим первый открытый UV Editor
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return {
                            'window': context.window,
                            'screen': context.screen,
                            'area': area,
                            'region': region,
                            'scene': context.scene,
                            'edit_object': context.edit_object
                        }
        return None


def update_uv_selection():
    bpy.ops.uv.reveal(select=True)
    bpy.ops.uv.select_all(action='DESELECT')
    bpy.ops.uv.select_linked()
    return None


# Панель для 3D View (View3D)
class VIEW3D_PT_my_tools_panel(bpy.types.Panel):
    bl_label = "My Tools"
    bl_idname = "VIEW3D_PT_my_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    def draw(self, context):
        layout = self.layout
        
        # Bevel Weight кнопки (теперь сверху)
        row = layout.row(align=True)
        row.label(text="Bevel Weight:")
        row.operator("mesh.set_bevel_weight_zero", text="0")
        row.operator("mesh.set_bevel_weight_one", text="1")
        
        # Crease кнопки (теперь снизу)
        row = layout.row(align=True)
        row.label(text="Crease:")
        row.operator("mesh.set_crease_zero", text="0")
        row.operator("mesh.set_crease_one", text="1")
        
        # Select Tools аккордеон
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "select_tools_expanded", 
                 icon="TRIA_DOWN" if context.scene.select_tools_expanded else "TRIA_RIGHT", 
                 text="Select Tools", emboss=False)
        
        if context.scene.select_tools_expanded:
            box.operator("mesh.select_crease_edges", text="Crease Edges")
            box.operator("mesh.select_bevel_weight_edges", text="Bevel Weight Edges")
            box.operator("mesh.select_sharp_edges", text="Marked Sharp Edges")
            box.operator("object.select_non_uniform_scale", text="Scaled Objects")
        
        # Length Settings аккордеон
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "length_settings_expanded", 
                 icon="TRIA_DOWN" if context.scene.length_settings_expanded else "TRIA_RIGHT", 
                 text="Unit Scene Settings", emboss=False)
        
        if context.scene.length_settings_expanded:
            unit_settings = context.scene.unit_settings
            
            # Единицы измерения длины
            col = box.column(align=True)
            col.prop(unit_settings, "length_unit", text="")
            
            # Масштаб единиц
            col.separator()
            col.prop(unit_settings, "scale_length", text="")

# Новая панель для UV Editing (Image Editor)
class IMAGE_EDITOR_PT_my_uv_tools(bpy.types.Panel):
    bl_label = "My UV Tools"
    bl_idname = "IMAGE_EDITOR_PT_my_uv_tools"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        layout.operator("uv.straight_uv_island", text="Straight UV Square")

# Регистрация классов
classes = (
    MESH_OT_select_crease_edges,
    MESH_OT_set_crease_one,
    MESH_OT_set_crease_zero,
    MESH_OT_set_bevel_weight_one,
    MESH_OT_set_bevel_weight_zero,
    MESH_OT_select_bevel_weight_edges,
    MESH_OT_select_sharp_edges,
    OBJECT_OT_select_non_uniform_scale,
    UV_OT_straight_uv_island,
    VIEW3D_PT_my_tools_panel,
    IMAGE_EDITOR_PT_my_uv_tools,
)

def register():
    # Регистрируем булевые свойства для состояния аккордеонов
    bpy.types.Scene.select_tools_expanded = bpy.props.BoolProperty(
        name="Select Tools Expanded",
        description="Показать/скрыть инструменты выбора",
        default=False
    )
    
    bpy.types.Scene.length_settings_expanded = bpy.props.BoolProperty(
        name="Length Settings Expanded",
        description="Показать/скрыть настройки единиц длины",
        default=False
    )
    
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Удаляем свойства при деактивации аддона
    del bpy.types.Scene.select_tools_expanded
    del bpy.types.Scene.length_settings_expanded

if __name__ == "__main__":
    register()