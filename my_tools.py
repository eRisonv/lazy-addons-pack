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

# Функция для получения и сохранения текущего режима выбора
def get_current_select_mode(context):
    """Получает текущий режим выбора в Edit Mode"""
    if context.mode == 'EDIT_MESH':
        tool_settings = context.tool_settings
        mesh_select_mode = tool_settings.mesh_select_mode
        if mesh_select_mode[0]:  # Vertex
            return 'VERT'
        elif mesh_select_mode[1]:  # Edge
            return 'EDGE'
        elif mesh_select_mode[2]:  # Face
            return 'FACE'
    return 'EDGE'  # По умолчанию

def restore_select_mode(context, original_mode):
    """Восстанавливает оригинальный режим выбора"""
    if context.mode == 'EDIT_MESH':
        bpy.ops.mesh.select_mode(type=original_mode)

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

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

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

        # Временно переключаемся на режим выбора ребер для операции
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        for edge in bm.edges:
            if edge[crease_layer] > self.threshold:
                edge.select = True

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
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

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой crease
        crease_layer = bm.edges.layers.float.get("crease_edge")
        if crease_layer is None:
            crease_layer = bm.edges.layers.float.new("crease_edge")

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[crease_layer] = 1.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
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

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой crease
        crease_layer = bm.edges.layers.float.get("crease_edge")
        if crease_layer is None:
            crease_layer = bm.edges.layers.float.new("crease_edge")

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[crease_layer] = 0.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
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

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой bevel_weight
        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            bevel_weight_layer = bm.edges.layers.float.new("bevel_weight_edge")

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[bevel_weight_layer] = 1.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
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

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слой bevel_weight
        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            bevel_weight_layer = bm.edges.layers.float.new("bevel_weight_edge")

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge[bevel_weight_layer] = 0.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
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

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            self.report({'WARNING'}, "Bevel Weight слой не найден")
            return {'CANCELLED'}

        # Временно переключаемся на режим выбора ребер для операции
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        selected_count = 0
        for edge in bm.edges:
            if edge[bevel_weight_layer] > 0.0:
                edge.select = True
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        return {'FINISHED'}

# Оператор: Выбор острых рёбер (Mark Sharp)
class MESH_OT_select_sharp_edges(bpy.types.Operator):
    bl_idname = "mesh.select_sharp_edges"
    bl_label = "Select Sharp Edges"
    bl_description = "Выбирает рёбра помеченные как Sharp (Mark Sharp). С зажатым Shift - выбор по углу"
    bl_options = {'REGISTER', 'UNDO'}

    # Свойство для угла при выборе по углу
    angle: bpy.props.FloatProperty(
        name="Angle",
        description="Максимальный угол между гранями для выбора ребра",
        default=0.523599,  # 30 градусов в радианах
        min=0.0,
        max=3.14159,  # 180 градусов в радианах
        step=1,
        precision=3,
        subtype='ANGLE',
        options={'SKIP_SAVE'}  # Не сохраняем в blend файл и не показываем когда не нужно
    )

    # Внутреннее свойство для определения режима
    _select_by_angle: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        # Временно переключаемся на режим выбора ребер для операции
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        if self._select_by_angle:
            # Выбираем рёбра по углу между гранями
            import mathutils
            selected_count = 0
            
            for edge in bm.edges:
                if len(edge.link_faces) == 2:  # Только рёбра между двумя гранями
                    face1 = edge.link_faces[0]
                    face2 = edge.link_faces[1]
                    angle = face1.normal.angle(face2.normal)
                    
                    if angle > self.angle:
                        edge.select = True
                        selected_count += 1
        else:
            # Выбираем рёбра с пометкой Mark Sharp
            selected_count = 0
            for edge in bm.edges:
                if not edge.smooth:  # edge.smooth = False означает Sharp
                    edge.select = True
                    selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        return {'FINISHED'}

    def draw(self, context):
        # Показываем настройку угла только при выборе по углу
        if self._select_by_angle:
            layout = self.layout
            layout.prop(self, "angle")

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def invoke(self, context, event):
        # Проверяем, зажат ли Shift
        if event.shift:
            # Устанавливаем режим выбора по углу
            self._select_by_angle = True
            # Выполняем операцию сразу, панель настроек появится автоматически снизу слева
            return self.execute(context)
        else:
            # Выполняем обычную логику (выбор помеченных как Sharp)
            self._select_by_angle = False
            return self.execute(context)

# Оператор: Mark Sharp для выделенных рёбер
class MESH_OT_mark_sharp(bpy.types.Operator):
    bl_idname = "mesh.mark_sharp_custom"
    bl_label = "Mark Sharp"
    bl_description = "Помечает выделенные рёбра как Sharp"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge.smooth = False  # False = Sharp
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        return {'FINISHED'}

# Оператор: Clear Sharp для выделенных рёбер
class MESH_OT_clear_sharp(bpy.types.Operator):
    bl_idname = "mesh.clear_sharp_custom"
    bl_label = "Clear Sharp"
    bl_description = "Убирает пометку Sharp с выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge.smooth = True  # True = Smooth (не Sharp)
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        return {'FINISHED'}

# Оператор: Mark Seam для выделенных рёбер
class MESH_OT_mark_seam(bpy.types.Operator):
    bl_idname = "mesh.mark_seam_custom"
    bl_label = "Mark Seam"
    bl_description = "Помечает выделенные рёбра как Seam"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge.seam = True
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        return {'FINISHED'}

# Оператор: Clear Seam для выделенных рёбер
class MESH_OT_clear_seam(bpy.types.Operator):
    bl_idname = "mesh.clear_seam_custom"
    bl_label = "Clear Seam"
    bl_description = "Убирает пометку Seam с выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                edge.seam = False
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        return {'FINISHED'}

class MESH_OT_unmark_all(bpy.types.Operator):
    bl_idname = "mesh.unmark_all"
    bl_label = "Unmark All"
    bl_description = "Снимает все пометки (Sharp, Seam, Bevel Weight, Crease) с выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}

        # Сохраняем текущий режим выбора
        original_mode = get_current_select_mode(context)

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Получаем или создаём слои
        crease_layer = bm.edges.layers.float.get("crease_edge")
        if crease_layer is None:
            crease_layer = bm.edges.layers.float.new("crease_edge")

        bevel_weight_layer = bm.edges.layers.float.get("bevel_weight_edge")
        if bevel_weight_layer is None:
            bevel_weight_layer = bm.edges.layers.float.new("bevel_weight_edge")

        selected_count = 0
        for edge in bm.edges:
            if edge.select:
                # Убираем Sharp
                edge.smooth = True
                # Убираем Seam
                edge.seam = False
                # Убираем Bevel Weight
                edge[bevel_weight_layer] = 0.0
                # Убираем Crease
                edge[crease_layer] = 0.0
                selected_count += 1

        bmesh.update_edit_mesh(mesh)
        
        # Восстанавливаем оригинальный режим выбора
        restore_select_mode(context, original_mode)
        
        self.report({'INFO'}, f"Unmarked {selected_count} edges")
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
        
        # Кнопка 0 - обычная
        row.operator("mesh.bevel_weight_zero_button", text="0")
        
        # Кнопка 1 - с синей обводкой как у bevel weight
        sub = row.row(align=True)
        #sub.alert = True  # Красная обводка
        sub.operator("mesh.bevel_weight_one_button", text="1")
        
        # Crease кнопки (теперь снизу)
        row = layout.row(align=True)
        row.label(text="Crease:")
        
        # Кнопка 0 - обычная
        row.operator("mesh.crease_zero_button", text="0")
        
        # Кнопка 1 - с красной обводкой как у crease
        sub = row.row(align=True)
        #sub.alert = True  # Красная обводка
        sub.operator("mesh.crease_one_button", text="1")
        
        # Select Tools аккордеон
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "select_tools_expanded", 
                 icon="TRIA_DOWN" if context.scene.select_tools_expanded else "TRIA_RIGHT", 
                 text="Select Tools", emboss=False)
        
        if context.scene.select_tools_expanded:
            box.operator("mesh.select_crease_edges", text="Crease Edges")
            box.operator("mesh.select_bevel_weight_edges", text="Bevel Weight Edges")
            box.operator("mesh.select_sharp_edges", text="Marked Sharp or Angle")
            box.operator("object.select_non_uniform_scale", text="Scaled Objects")
            
            # Небольшой отступ перед новыми кнопками
            box.separator(factor=0.5)
            
            # Новые кнопки Mark Sharp - Clear Sharp
            row = box.row(align=True)
            row.operator("mesh.mark_sharp_custom", text="Mark Sharp")
            row.operator("mesh.clear_sharp_custom", text="Clear Sharp")
            
            # Новые кнопки Mark Seam - Clear Seam
            row = box.row(align=True)
            row.operator("mesh.mark_seam_custom", text="Mark Seam")
            row.operator("mesh.clear_seam_custom", text="Clear Seam")
            box.separator(factor=0.5)
            box.operator("mesh.unmark_all", text="Unmark All")
            
        
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

# Кастомные операторы для кнопок с цветом
class MESH_OT_bevel_weight_zero_button(bpy.types.Operator):
    bl_idname = "mesh.bevel_weight_zero_button"
    bl_label = "0"
    bl_description = "Устанавливает Bevel Weight в 0 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.mesh.set_bevel_weight_zero()

class MESH_OT_bevel_weight_one_button(bpy.types.Operator):
    bl_idname = "mesh.bevel_weight_one_button"
    bl_label = "1"
    bl_description = "Устанавливает Bevel Weight в 1 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.mesh.set_bevel_weight_one()

class MESH_OT_crease_zero_button(bpy.types.Operator):
    bl_idname = "mesh.crease_zero_button"
    bl_label = "0"
    bl_description = "Устанавливает Crease в 0 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.mesh.set_crease_zero()

class MESH_OT_crease_one_button(bpy.types.Operator):
    bl_idname = "mesh.crease_one_button"
    bl_label = "1"
    bl_description = "Устанавливает Crease в 1 для выделенных рёбер"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.mesh.set_crease_one()

# Регистрация классов
classes = (
    MESH_OT_select_crease_edges,
    MESH_OT_set_crease_one,
    MESH_OT_set_crease_zero,
    MESH_OT_set_bevel_weight_one,
    MESH_OT_set_bevel_weight_zero,
    MESH_OT_select_bevel_weight_edges,
    MESH_OT_select_sharp_edges,
    MESH_OT_unmark_all,
    MESH_OT_mark_sharp,
    MESH_OT_clear_sharp,
    MESH_OT_mark_seam,
    MESH_OT_clear_seam,
    OBJECT_OT_select_non_uniform_scale,
    UV_OT_straight_uv_island,
    MESH_OT_bevel_weight_zero_button,
    MESH_OT_bevel_weight_one_button,
    MESH_OT_crease_zero_button,
    MESH_OT_crease_one_button,
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