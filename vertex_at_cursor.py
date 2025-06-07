bl_info = {
    "name": "Add Vertex at Cursor",
    "author": "Distortion",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Edit Mode > Right Click > Add Vertex at Mouse",
    "description": "Добавляет вертекс на выбранном или ближайшем ребре к курсору",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector
from bpy_extras import view3d_utils

class MESH_OT_add_vertex_at_cursor(bpy.types.Operator):
    """Добавить вертекс на выбранном ребре или ближайшем к курсору ребре"""
    bl_idname = "mesh.add_vertex_at_cursor"
    bl_label = "Add Vertex at Mouse"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def is_edge_visible_solid_mode(self, context, edge, obj, bm):
        """Упрощенная проверка видимости ребра в Solid режиме"""
        region = context.region
        rv3d = context.region_data
        
        # Получаем центр ребра
        edge_center_local = (edge.verts[0].co + edge.verts[1].co) / 2
        edge_center_world = obj.matrix_world @ edge_center_local
        
        # Проверяем, что ребро находится перед камерой
        view_matrix = rv3d.view_matrix
        edge_center_view = view_matrix @ edge_center_world.to_4d()
        
        # Если ребро за камерой, оно не видимо
        if edge_center_view.z > 0:
            return False
        
        # Проверяем нормали граней, связанных с ребром
        edge_faces = edge.link_faces
        
        if not edge_faces:
            # Если ребро не связано с гранями, считаем его видимым
            return True
        
        # Получаем направление взгляда
        view_location = view_matrix.inverted().translation
        
        # Проверяем, есть ли хотя бы одна видимая грань
        for face in edge_faces:
            # Получаем нормаль грани в мировых координатах
            face_normal_world = obj.matrix_world.to_3x3() @ face.normal
            face_normal_world.normalize()
            
            # Получаем центр грани
            face_center_world = obj.matrix_world @ face.calc_center_median()
            
            # Вектор от центра грани к камере
            to_camera = (view_location - face_center_world).normalized()
            
            # Если нормаль грани направлена к камере, грань видима
            if face_normal_world.dot(to_camera) > 0:
                return True
        
        return False
    
    def find_closest_edge_to_cursor(self, context, mouse_coord, bm, obj):
        """Находит ближайшее к курсору видимое ребро"""
        region = context.region
        rv3d = context.region_data
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        
        # Проверяем все ребра
        for edge in bm.edges:
            # Сначала проверяем видимость ребра в Solid режиме
            if not self.is_edge_visible_solid_mode(context, edge, obj, bm):
                continue
            
            # Получаем вертексы ребра в мировых координатах
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            
            # Проецируем на экран
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if screen_v1 and screen_v2:
                # Дополнительная проверка: убеждаемся, что оба конца ребра находятся перед камерой
                # Проверяем Z-координаты в координатах вида
                v1_view = rv3d.view_matrix @ v1_world.to_4d()
                v2_view = rv3d.view_matrix @ v2_world.to_4d()
                
                # Если оба конца ребра за камерой (z > 0 в координатах вида), пропускаем
                if v1_view.z > 0 and v2_view.z > 0:
                    continue
                
                # Вычисляем расстояние от курсора до ребра на экране
                screen_edge_vec = screen_v2 - screen_v1
                screen_edge_length_sq = screen_edge_vec.length_squared
                
                if screen_edge_length_sq > 1e-6:
                    mouse_vec = Vector(mouse_coord)
                    to_mouse = mouse_vec - screen_v1
                    t = to_mouse.dot(screen_edge_vec) / screen_edge_length_sq
                    
                    # Ограничиваем t в пределах ребра
                    t_clamped = max(0.0, min(1.0, t))
                    
                    # Находим ближайшую точку на ребре
                    closest_point_on_edge = screen_v1 + t_clamped * screen_edge_vec
                    distance = (mouse_vec - closest_point_on_edge).length
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_edge = edge
                        # Предотвращаем создание дублирующих вертексов на концах
                        best_t = max(0.05, min(0.95, t))
        
        return closest_edge, best_t, min_distance
    
    def execute(self, context):
        obj = context.active_object
        
        # Получаем позицию курсора мыши
        mouse_coord = getattr(self, 'mouse_coord', None)
        
        if not mouse_coord:
            self.report({'WARNING'}, "Не удалось получить позицию курсора")
            return {'CANCELLED'}
        
        # Получаем bmesh из edit mode
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Обновляем все lookup tables и индексы
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        # Обновляем нормали для корректной проверки видимости
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        
        # Определяем текущий режим выбора
        select_mode = context.tool_settings.mesh_select_mode
        is_edge_mode = select_mode[1]  # Edge mode
        is_vertex_mode = select_mode[0]  # Vertex mode
        
        target_edge = None
        t = 0.5
        
        if is_edge_mode:
            # Режим ребер - работаем с выбранными ребрами
            selected_edges = [edge for edge in bm.edges if edge.select]
            
            if not selected_edges:
                self.report({'ERROR'}, "Не выбрано ни одного ребра")
                return {'CANCELLED'}
            
            if len(selected_edges) > 1:
                self.report({'ERROR'}, "Выберите только одно ребро")
                return {'CANCELLED'}
            
            target_edge = selected_edges[0]
            
            # Вычисляем позицию на выбранном ребре
            region = context.region
            rv3d = context.region_data
            
            # Получаем вертексы ребра в мировых координатах
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            
            # Проецируем на экран
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if screen_v1 and screen_v2:
                screen_edge_vec = screen_v2 - screen_v1
                screen_edge_length_sq = screen_edge_vec.length_squared
                
                if screen_edge_length_sq > 1e-6:
                    mouse_vec = Vector(mouse_coord)
                    to_mouse = mouse_vec - screen_v1
                    t = to_mouse.dot(screen_edge_vec) / screen_edge_length_sq
                    
                    # Проверяем расстояние до ребра
                    closest_point_on_edge = screen_v1 + max(0, min(1, t)) * screen_edge_vec
                    distance_to_edge = (mouse_vec - closest_point_on_edge).length
                    
                    # ИЗМЕНЕНИЕ: если курсор слишком далеко, ставим вертекс по середине ребра
                    if distance_to_edge > 50:
                        t = 0.5  # Ставим по середине
                        self.report({'INFO'}, "Курсор далеко от ребра - вертекс добавлен по середине")
                    else:
                        # Предотвращаем создание дублирующих вертексов на концах
                        t = max(0.05, min(0.95, t))
            
        elif is_vertex_mode:
            # Режим вертексов - ищем ближайшее к курсору ребро
            print(f"Vertex mode: проверяем {len(bm.edges)} ребер")
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor(context, mouse_coord, bm, obj)
            
            if not closest_edge:
                print("Не найдено видимых ребер")
                self.report({'ERROR'}, "Не найдено подходящих ребер")
                return {'CANCELLED'}
            
            # Проверяем, что курсор достаточно близко к ребру
            if min_distance > 50:  # 50 пикселей
                print(f"Ближайшее ребро слишком далеко: {min_distance} пикселей")
                self.report({'WARNING'}, "Курсор слишком далеко от ближайшего ребра")
                return {'CANCELLED'}
            
            print(f"Найдено подходящее ребро на расстоянии {min_distance} пикселей")
            target_edge = closest_edge
            t = best_t
            
        else:
            # Режим граней - также ищем ближайшее ребро
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor(context, mouse_coord, bm, obj)
            
            if not closest_edge:
                self.report({'ERROR'}, "Не найдено подходящих ребер")
                return {'CANCELLED'}
            
            if min_distance > 50:
                self.report({'WARNING'}, "Курсор слишком далеко от ближайшего ребра")
                return {'CANCELLED'}
            
            target_edge = closest_edge
            t = best_t
        
        # Теперь у нас есть target_edge и параметр t
        if not target_edge:
            self.report({'ERROR'}, "Не удалось определить целевое ребро")
            return {'CANCELLED'}
        
        # Получаем вертексы ребра
        v1 = target_edge.verts[0].co
        v2 = target_edge.verts[1].co
        
        # Вычисляем позицию нового вертекса в локальных координатах
        new_pos_local = v1 + t * (v2 - v1)
        
        # Разделяем ребро
        new_vert = bmesh.utils.edge_split(target_edge, target_edge.verts[0], t)[1]
        new_vert.co = new_pos_local
        
        # Обновляем bmesh индексы после изменения геометрии
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        # Снимаем выделение со всех элементов
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        # Выделяем новый вертекс если мы в режиме вертексов
        if is_vertex_mode:
            new_vert.select = True
        else:
            # В режиме ребер выделяем одно из новых ребер
            if new_vert.link_edges:
                # Выбираем ребро в зависимости от позиции курсора
                if t > 0.5 and len(new_vert.link_edges) > 1:
                    # Выбираем ребро, которое ведёт ко второму вертексу
                    for edge in new_vert.link_edges:
                        if any(v.co == v2 for v in edge.verts):
                            edge.select = True
                            break
                else:
                    # Выбираем первое ребро
                    new_vert.link_edges[0].select = True
        
        # Обновляем меш и принудительно обновляем viewport
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        
        # Принудительно обновляем область просмотра
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
       
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Сохраняем координаты мыши
        self.mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        return self.execute(context)

def menu_func(self, context):
    """Функция для добавления пункта в контекстное меню"""
    self.layout.operator(MESH_OT_add_vertex_at_cursor.bl_idname)

def register():
    bpy.utils.register_class(MESH_OT_add_vertex_at_cursor)
    # Добавляем в контекстное меню (правая кнопка мыши)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_class(MESH_OT_add_vertex_at_cursor)
    # Удаляем из контекстного меню
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()