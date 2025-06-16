bl_info = {
    "name": "Add Vertex at Cursor",
    "author": "eRisonv",
    "version": (1, 3),
    "blender": (2, 80, 0),
    "location": "Edit Mode > Right Click > Add Vertex at Mouse / Connect Selected Vertex at Cursor",
    "description": "Adds vertex on selected/closest edge to cursor with precise positioning",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector
import mathutils
from bpy_extras import view3d_utils
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

class MESH_OT_add_vertex_at_cursor(bpy.types.Operator):
    """Add vertex on selected edge or closest to cursor edge"""
    bl_idname = "mesh.add_vertex_at_cursor"
    bl_label = "Add Vertex at Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def cast_ray_from_cursor(self, context, mouse_coord):
        """Создаёт луч от курсора в 3D пространство"""
        region = context.region
        rv3d = context.region_data
        
        # Получаем направление луча от курсора
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)
        
        return ray_origin, ray_direction
    
    def point_to_line_distance_3d(self, point, line_start, line_end):
        """Вычисляет кратчайшее расстояние от точки до линии в 3D и параметр t"""
        line_vec = line_end - line_start
        line_len_sq = line_vec.length_squared
        
        if line_len_sq < 1e-6:
            return (point - line_start).length, 0.0
        
        point_vec = point - line_start
        t = point_vec.dot(line_vec) / line_len_sq
        t_clamped = max(0.0, min(1.0, t))
        
        closest_point = line_start + t_clamped * line_vec
        distance = (point - closest_point).length
        
        return distance, t
    
    def ray_to_line_closest_points(self, ray_origin, ray_direction, line_start, line_end):
        """Находит ближайшие точки между лучом и отрезком в 3D"""
        line_vec = line_end - line_start
        w0 = ray_origin - line_start
        
        a = ray_direction.dot(ray_direction)
        b = ray_direction.dot(line_vec)
        c = line_vec.dot(line_vec)
        d = ray_direction.dot(w0)
        e = line_vec.dot(w0)
        
        denominator = a * c - b * b
        
        if abs(denominator) < 1e-6:
            # Линии параллельны
            t_line = 0.0
            t_ray = d / a if abs(a) > 1e-6 else 0.0
        else:
            t_ray = (b * e - c * d) / denominator
            t_line = (a * e - b * d) / denominator
        
        # Ограничиваем t_line отрезком [0, 1]
        t_line = max(0.0, min(1.0, t_line))
        
        point_on_ray = ray_origin + t_ray * ray_direction
        point_on_line = line_start + t_line * line_vec
        
        distance = (point_on_ray - point_on_line).length
        
        return distance, t_line, point_on_line

    def is_vertex_really_visible(self, context, vert, obj, bm):
        """Простая проверка видимости вершины"""
        region = context.region
        rv3d = context.region_data
        
        vert_world = obj.matrix_world @ vert.co
        
        # Проверяем, что вершина перед камерой
        vert_view = rv3d.view_matrix @ vert_world.to_4d()
        if vert_view.z > 0:
            return False
        
        # Raycast от камеры к вершине
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (region.width/2, region.height/2))
        ray_direction = (vert_world - ray_origin).normalized()
        distance = (vert_world - ray_origin).length
        
        success, hit_location, hit_normal, hit_index = obj.ray_cast(
            ray_origin, ray_direction, distance=distance
        )
        
        if not success:
            return True
        
        # Проверяем, не слишком ли близко препятствие
        distance_to_hit = (hit_location - ray_origin).length
        return distance_to_hit >= distance - 0.001
    
    def is_edge_visible_like_knife(self, context, edge, obj, bm):
        """Проверка видимости ребра как в инструменте Knife"""
        region = context.region
        rv3d = context.region_data
        
        # Получаем мировые координаты вершин
        v1_world = obj.matrix_world @ edge.verts[0].co
        v2_world = obj.matrix_world @ edge.verts[1].co
        
        # Проверяем, что обе вершины перед камерой
        v1_view = rv3d.view_matrix @ v1_world.to_4d()
        v2_view = rv3d.view_matrix @ v2_world.to_4d()
        if v1_view.z > 0 or v2_view.z > 0:
            return False
        
        # Проецируем на экран
        screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
        screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
        if not screen_v1 or not screen_v2:
            return False
        
        # Проверяем несколько точек вдоль ребра (как делает Knife)
        test_points = 5
        for i in range(test_points):
            t = i / (test_points - 1)
            test_point_world = v1_world.lerp(v2_world, t)
            screen_point = view3d_utils.location_3d_to_region_2d(region, rv3d, test_point_world)
            
            if not screen_point:
                continue
            
            # Raycast от курсора вглубь сцены (как делает Knife)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, screen_point)
            ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, screen_point)
            
            # Выполняем raycast
            success, hit_location, hit_normal, hit_index = obj.ray_cast(
                ray_origin, ray_direction, distance=1000.0
            )
            
            if success:
                # Проверяем, что первое попадание - это наша тестовая точка
                distance_to_test = (test_point_world - ray_origin).length
                distance_to_hit = (hit_location - ray_origin).length
                
                # Если разница больше допустимой погрешности, значит ребро скрыто
                if abs(distance_to_test - distance_to_hit) > 0.001:
                    return False
        
        return True

    def is_point_visible(self, context, point_world, obj, ray_origin):
        """Проверяет, видима ли точка с камеры"""
        ray_direction = (point_world - ray_origin).normalized()
        distance = (point_world - ray_origin).length
        
        success, hit_location, _, _ = obj.ray_cast(ray_origin, ray_direction, distance=distance)
        
        if not success:
            return True
        hit_distance = (hit_location - ray_origin).length
        return hit_distance >= distance - 0.001

    def is_edge_visible(self, context, edge, obj, bm, ray_origin, ray_direction):
        """Проверяет, видимо ли ребро"""
        v1_world = obj.matrix_world @ edge.verts[0].co
        v2_world = obj.matrix_world @ edge.verts[1].co
        mid_point = v1_world.lerp(v2_world, 0.5)
        return self.is_point_visible(context, mid_point, obj, ray_origin)
    
    def find_closest_edge_to_cursor(self, context, mouse_coord, bm, obj):
        region = context.region
        rv3d = context.region_data
        
        # Получаем позицию камеры
        camera_pos = rv3d.view_matrix.inverted().translation
        
        # Бросаем луч от курсора
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)
        
        # Находим первую грань, в которую попал луч
        success, hit_location, hit_normal, hit_index = obj.ray_cast(ray_origin, ray_direction)
        if not success:
            return None, 0.5, float('inf')
        
        # Берём рёбра только первой грани
        hit_face = bm.faces[hit_index]
        candidate_edges = hit_face.edges
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        
        for edge in candidate_edges:
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            
            # Проверяем видимость нескольких точек на ребре
            visible = True
            for t in [0.0, 0.5, 1.0]:  # Проверяем начало, середину и конец
                test_point = v1_world.lerp(v2_world, t)
                if not self.is_point_visible(context, test_point, obj, camera_pos):
                    visible = False
                    break
            if not visible:
                continue
            
            # Проверяем расстояние до ребра на экране
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if not screen_v1 or not screen_v2:
                continue
            
            edge_vec = screen_v2 - screen_v1
            cursor_vec = Vector(mouse_coord) - screen_v1
            t = max(0.0, min(1.0, cursor_vec.dot(edge_vec) / edge_vec.length_squared))
            closest_point = screen_v1 + t * edge_vec
            distance = (Vector(mouse_coord) - closest_point).length
            
            if distance < min_distance:
                min_distance = distance
                closest_edge = edge
                best_t = t
        
        if closest_edge and min_distance <= 50:  # Допустимая дистанция в пикселях
            return closest_edge, best_t, min_distance
        return None, 0.5, float('inf')
    
    def execute(self, context):
        obj = context.active_object
        mouse_coord = getattr(self, 'mouse_coord', None)
        if not mouse_coord:
            self.report({'WARNING'}, "Could not get cursor position")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        select_mode = context.tool_settings.mesh_select_mode
        is_edge_mode = select_mode[1]
        is_vertex_mode = select_mode[0]
        
        target_edge = None
        t = 0.5
        
        if is_edge_mode:
            selected_edges = [edge for edge in bm.edges if edge.select]
            if not selected_edges:
                self.report({'ERROR'}, "No edge selected")
                return {'CANCELLED'}
            if len(selected_edges) > 1:
                self.report({'ERROR'}, "Select only one edge")
                return {'CANCELLED'}
            
            target_edge = selected_edges[0]
            
            # Проецируем вершины ребра в экранное пространство
            region = context.region
            rv3d = context.region_data
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if screen_v1 and screen_v2:
                edge_vec = screen_v2 - screen_v1
                edge_len_sq = edge_vec.length_squared
                
                if edge_len_sq > 1e-6:  # Проверка на ненулевую длину
                    cursor_vec = Vector(mouse_coord)
                    point_vec = cursor_vec - screen_v1
                    t = max(0.0, min(1.0, point_vec.dot(edge_vec) / edge_len_sq))
                    
                    # Проверяем расстояние до ребра в экранном пространстве
                    closest_point = screen_v1 + t * edge_vec
                    cursor_distance = (cursor_vec - closest_point).length
                    if cursor_distance > 50:
                        t = 0.5
                        self.report({'INFO'}, "Cursor far from edge - vertex added at center")
                    else:
                        t = max(0.05, min(0.95, t))  # Ограничиваем t как раньше
                else:
                    t = 0.5
            else:
                t = 0.5
                
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor_knife_style(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "No suitable edges found")
                return {'CANCELLED'}
            if min_distance > 100:  # Увеличили толерантность для 3D расстояния
                self.report({'WARNING'}, "Cursor too far from closest edge")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        
        if not target_edge:
            self.report({'ERROR'}, "Could not determine target edge")
            return {'CANCELLED'}
        
        # Создаём новую вершину
        v1 = target_edge.verts[0].co
        v2 = target_edge.verts[1].co
        new_pos_local = v1 + t * (v2 - v1)
        new_vert = bmesh.utils.edge_split(target_edge, target_edge.verts[0], t)[1]
        new_vert.co = new_pos_local
        
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        # Очистка выделений
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        # Выделение в зависимости от режима
        if is_vertex_mode:
            new_vert.select = True
        else:
            if new_vert.link_edges:
                if t > 0.5 and len(new_vert.link_edges) > 1:
                    for edge in new_vert.link_edges:
                        if any(v.co == v2 for v in edge.verts):
                            edge.select = True
                            break
                else:
                    new_vert.link_edges[0].select = True
        
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'ERROR'}, "Этот оператор требует 3D-вид")
            return {'CANCELLED'}
        
        self.mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        return self.execute(context)

class MESH_OT_connect_selected_vertex_at_cursor(bpy.types.Operator):
    """Add vertex on selected edge or closest to cursor edge and connect to selected vertices"""
    bl_idname = "mesh.connect_selected_vertex_at_cursor"
    bl_label = "Connect Selected Vertex at Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def cast_ray_from_cursor(self, context, mouse_coord):
        """Создаёт луч от курсора в 3D пространство"""
        region = context.region
        rv3d = context.region_data
        
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)
        
        return ray_origin, ray_direction
        
    def is_vertex_visible(self, context, vert, obj, bm):
        """Проверяет, виден ли вертекс с точки зрения камеры, учитывая нормали"""
        region = context.region
        rv3d = context.region_data
        vert_world = obj.matrix_world @ vert.co
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (region.width/2, region.height/2))
        ray_direction = (vert_world - ray_origin).normalized()
        distance = (vert_world - ray_origin).length + 0.001
        
        success, location, normal, index = obj.ray_cast(ray_origin, ray_direction, distance=distance)
        
        if not success:
            return True  # Raycast не попал в грань — вертекс виден
        
        hit_face = bm.faces[index] if index >= 0 else None
        if hit_face in vert.link_faces:
            # Проверяем, что нормаль грани смотрит в сторону камеры
            face_normal_world = obj.matrix_world.to_3x3() @ hit_face.normal
            view_direction = (ray_origin - vert_world).normalized()
            if face_normal_world.dot(view_direction) > 0:
                return True  # Нормаль смотрит в сторону камеры — вертекс виден
        return False  # Вершина перекрыта или нормаль смотрит в другую сторону
    
    def ray_to_line_closest_points(self, ray_origin, ray_direction, line_start, line_end):
        """Находит ближайшие точки между лучом и отрезком в 3D"""
        line_vec = line_end - line_start
        w0 = ray_origin - line_start
        
        a = ray_direction.dot(ray_direction)
        b = ray_direction.dot(line_vec)
        c = line_vec.dot(line_vec)
        d = ray_direction.dot(w0)
        e = line_vec.dot(w0)
        
        denominator = a * c - b * b
        
        if abs(denominator) < 1e-6:
            t_line = 0.0
            t_ray = d / a if abs(a) > 1e-6 else 0.0
        else:
            t_ray = (b * e - c * d) / denominator
            t_line = (a * e - b * d) / denominator
        
        t_line = max(0.0, min(1.0, t_line))
        
        point_on_ray = ray_origin + t_ray * ray_direction
        point_on_line = line_start + t_line * line_vec
        
        distance = (point_on_ray - point_on_line).length
        
        return distance, t_line, point_on_line

    def is_vertex_really_visible(self, context, vert, obj, bm):
        """Простая проверка видимости вершины"""
        region = context.region
        rv3d = context.region_data
        
        vert_world = obj.matrix_world @ vert.co
        
        # Проверяем, что вершина перед камерой
        vert_view = rv3d.view_matrix @ vert_world.to_4d()
        if vert_view.z > 0:
            return False
        
        # Raycast от камеры к вершине
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (region.width/2, region.height/2))
        ray_direction = (vert_world - ray_origin).normalized()
        distance = (vert_world - ray_origin).length
        
        success, hit_location, hit_normal, hit_index = obj.ray_cast(
            ray_origin, ray_direction, distance=distance
        )
        
        if not success:
            return True
        
        # Проверяем, не слишком ли близко препятствие
        distance_to_hit = (hit_location - ray_origin).length
        return distance_to_hit >= distance - 0.001
    
    def is_edge_visible_like_knife(self, context, edge, obj, bm):
        """Проверка видимости ребра как в инструменте Knife"""
        region = context.region
        rv3d = context.region_data
        
        # Получаем мировые координаты вершин
        v1_world = obj.matrix_world @ edge.verts[0].co
        v2_world = obj.matrix_world @ edge.verts[1].co
        
        # Проверяем, что обе вершины перед камерой
        v1_view = rv3d.view_matrix @ v1_world.to_4d()
        v2_view = rv3d.view_matrix @ v2_world.to_4d()
        if v1_view.z > 0 or v2_view.z > 0:
            return False
        
        # Проецируем на экран
        screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
        screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
        if not screen_v1 or not screen_v2:
            return False
        
        # Проверяем несколько точек вдоль ребра (как делает Knife)
        test_points = 5
        for i in range(test_points):
            t = i / (test_points - 1)
            test_point_world = v1_world.lerp(v2_world, t)
            screen_point = view3d_utils.location_3d_to_region_2d(region, rv3d, test_point_world)
            
            if not screen_point:
                continue
            
            # Raycast от курсора вглубь сцены (как делает Knife)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, screen_point)
            ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, screen_point)
            
            # Выполняем raycast
            success, hit_location, hit_normal, hit_index = obj.ray_cast(
                ray_origin, ray_direction, distance=1000.0
            )
            
            if success:
                # Проверяем, что первое попадание - это наша тестовая точка
                distance_to_test = (test_point_world - ray_origin).length
                distance_to_hit = (hit_location - ray_origin).length
                
                # Если разница больше допустимой погрешности, значит ребро скрыто
                if abs(distance_to_test - distance_to_hit) > 0.001:
                    return False
        
        return True

    def is_point_visible(self, context, point_world, obj, ray_origin):
        """Проверяет, видима ли точка с камеры"""
        ray_direction = (point_world - ray_origin).normalized()
        distance = (point_world - ray_origin).length
        
        success, hit_location, _, _ = obj.ray_cast(ray_origin, ray_direction, distance=distance)
        
        if not success:
            return True
        hit_distance = (hit_location - ray_origin).length
        return hit_distance >= distance - 0.001

    def is_edge_visible(self, context, edge, obj, bm, ray_origin, ray_direction):
        """Проверяет, видимо ли ребро"""
        v1_world = obj.matrix_world @ edge.verts[0].co
        v2_world = obj.matrix_world @ edge.verts[1].co
        mid_point = v1_world.lerp(v2_world, 0.5)
        return self.is_point_visible(context, mid_point, obj, ray_origin)
    
    def find_closest_edge_to_cursor_knife_style(self, context, mouse_coord, bm, obj):
        region = context.region
        rv3d = context.region_data
        
        # Бросаем луч от курсора
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)
        
        # Находим первую грань, в которую попал луч
        success, hit_location, hit_normal, hit_index = obj.ray_cast(ray_origin, ray_direction, distance=10000.0)
        
        candidate_edges = set()
        
        if success and hit_index >= 0:
            # Берём рёбра первой попавшейся грани
            hit_face = bm.faces[hit_index]
            candidate_edges.update(hit_face.edges)
        else:
            # Если луч не попал, ищем видимые рёбра
            for edge in bm.edges:
                if self.is_edge_visible(context, edge, obj, bm, ray_origin, ray_direction):
                    candidate_edges.add(edge)
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        
        for edge in candidate_edges:
            # Пропускаем рёбра на задних гранях (нормаль от камеры)
            if not any(face.normal.dot(ray_direction) < 0 for face in edge.link_faces):
                continue
            
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if not screen_v1 or not screen_v2:
                continue
            
            edge_vec = screen_v2 - screen_v1
            edge_len_sq = edge_vec.length_squared
            
            if edge_len_sq < 1e-6:
                continue
            
            cursor_vec = Vector(mouse_coord)
            point_vec = cursor_vec - screen_v1
            t = max(0.0, min(1.0, point_vec.dot(edge_vec) / edge_len_sq))
            
            closest_point = screen_v1 + t * edge_vec
            distance = (cursor_vec - closest_point).length
            
            # Проверяем, что ребро не перекрыто
            test_point_world = v1_world.lerp(v2_world, t)
            if not self.is_point_visible(context, test_point_world, obj, ray_origin):
                continue
            
            if distance < min_distance:
                min_distance = distance
                closest_edge = edge
                best_t = t
        
        max_tolerance = 100  # Настраиваемый порог в пикселях
        if closest_edge and min_distance <= max_tolerance:
            return closest_edge, best_t, min_distance
        else:
            return None, 0.5, float('inf')
    
    def find_vertex_under_cursor(self, context, mouse_coord, bm, obj, tolerance=30):
        """Находит вершину под курсором с более простой логикой."""
        region = context.region
        rv3d = context.region_data
        
        closest_vertex = None
        min_distance = float('inf')
        
        # Просто ищем ближайшую вершину к курсору на экране
        for vert in bm.verts:
            # Проверяем базовую видимость вершины
            if not self.is_vertex_visible(context, vert, obj, bm):
                continue
                
            # Получаем координаты вершины на экране
            vert_world = obj.matrix_world @ vert.co
            screen_coord = view3d_utils.location_3d_to_region_2d(region, rv3d, vert_world)
            
            if screen_coord:
                # Вычисляем расстояние от курсора до вершины на экране
                distance = (Vector(mouse_coord) - screen_coord).length
                if distance < tolerance and distance < min_distance:
                    min_distance = distance
                    closest_vertex = vert
        
        return closest_vertex, min_distance
    
    def execute(self, context):
        obj = context.active_object
        mouse_coord = getattr(self, 'mouse_coord', None)
        if not mouse_coord:
            self.report({'WARNING'}, "Could not get cursor position")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        selected_vertices = [v for v in bm.verts if v.select]
        
        vertex_under_cursor, cursor_distance = self.find_vertex_under_cursor(context, mouse_coord, bm, obj, tolerance=35)
        
        if not vertex_under_cursor:
            vertex_under_cursor, cursor_distance = self.find_vertex_under_cursor(context, mouse_coord, bm, obj, tolerance=20)
        
        # ИСПРАВЛЕНО: Обработка случая когда выбрано 2+ вертекса и мышь на любом вертексе (включая выделенные)
        if len(selected_vertices) >= 2 and vertex_under_cursor:
            connections_created = 0
            
            # Соединяем все выбранные вертексы с вертексом под курсором (кроме самого себя)
            for selected_vert in selected_vertices:
                if selected_vert == vertex_under_cursor:
                    continue  # Пропускаем если это тот же вертекс
                    
                # Проверяем, не существует ли уже ребро между вертексами
                edge_exists = False
                for edge in selected_vert.link_edges:
                    if vertex_under_cursor in edge.verts:
                        edge_exists = True
                        break
                
                if not edge_exists:
                    try:
                        # Пытаемся соединить через bmesh операции
                        result = bmesh.ops.connect_vert_pair(bm, verts=[selected_vert, vertex_under_cursor])
                        if result.get('edges'):
                            connections_created += 1
                    except:
                        try:
                            result = bmesh.ops.connect_verts(bm, verts=[selected_vert, vertex_under_cursor])
                            if result.get('edges'):
                                connections_created += 1
                        except:
                            # Если bmesh операции не работают, создаем ребро напрямую
                            try:
                                new_edge = bm.edges.new([selected_vert, vertex_under_cursor])
                                connections_created += 1
                            except ValueError:
                               
                                pass
            
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.normal_update()
            
            for e in bm.edges:
                e.select = False
            for v in bm.verts:
                v.select = False
            for f in bm.faces:
                f.select = False
            
            vertex_under_cursor.select = True
            bm.select_history.clear()
            bm.select_history.add(vertex_under_cursor)
            
            bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            if connections_created == 0:
                self.report({'WARNING'}, "No new connections could be created")
            
            return {'FINISHED'}
        
        # Случай когда выбран 1 вертекс и мышь на другом вертексе
        elif len(selected_vertices) == 1 and vertex_under_cursor and vertex_under_cursor != selected_vertices[0]:
            selected_vert = selected_vertices[0]
            
            # Проверяем, не существует ли уже ребро
            edge_exists = False
            for edge in selected_vert.link_edges:
                if vertex_under_cursor in edge.verts:
                    edge_exists = True
                    break
            
            if not edge_exists:
                try:
                    result = bmesh.ops.connect_vert_pair(bm, verts=[selected_vert, vertex_under_cursor])
                    if result.get('edges'):
                        connections_created = 1
                    else:
                        connections_created = 0
                except:
                    try:
                        result = bmesh.ops.connect_verts(bm, verts=[selected_vert, vertex_under_cursor])
                        if result.get('edges'):
                            connections_created = 1
                        else:
                            connections_created = 0
                    except:
                        try:
                            bm.edges.new([selected_vert, vertex_under_cursor])
                            connections_created = 1
                        except ValueError:
                            connections_created = 0
                
                bm.edges.ensure_lookup_table()
                bm.verts.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                
                for e in bm.edges:
                    e.select = False
                for v in bm.verts:
                    v.select = False
                for f in bm.faces:
                    f.select = False
                
                vertex_under_cursor.select = True
                bm.select_history.clear()
                bm.select_history.add(vertex_under_cursor)
                
                bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "Vertices are already connected")
                return {'FINISHED'}
        
        select_mode = context.tool_settings.mesh_select_mode
        is_edge_mode = select_mode[1]
        
        target_edge = None
        t = 0.5
        
        if is_edge_mode:
            selected_edges = [edge for edge in bm.edges if edge.select]
            if not selected_edges:
                self.report({'ERROR'}, "No edge selected")
                return {'CANCELLED'}
            if len(selected_edges) > 1:
                self.report({'ERROR'}, "Select only one edge")
                return {'CANCELLED'}
            
            target_edge = selected_edges[0]
            
            # Проецируем вершины ребра в экранное пространство
            region = context.region
            rv3d = context.region_data
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if screen_v1 and screen_v2:
                edge_vec = screen_v2 - screen_v1
                edge_len_sq = edge_vec.length_squared
                
                if edge_len_sq > 1e-6:  # Проверка на ненулевую длину
                    cursor_vec = Vector(mouse_coord)
                    point_vec = cursor_vec - screen_v1
                    t = max(0.0, min(1.0, point_vec.dot(edge_vec) / edge_len_sq))
                    
                    # Проверяем расстояние до ребра в экранном пространстве
                    closest_point = screen_v1 + t * edge_vec
                    cursor_distance = (cursor_vec - closest_point).length
                    if cursor_distance > 50:
                        t = 0.5
                        self.report({'INFO'}, "Cursor far from edge - vertex added at center")
                    else:
                        t = max(0.05, min(0.95, t))  # Ограничиваем t как раньше
                else:
                    t = 0.5
            else:
                t = 0.5
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor_knife_style(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "No suitable edges found")
                return {'CANCELLED'}
            if min_distance > 100:
                self.report({'WARNING'}, "Cursor too far from closest edge")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        
        if not target_edge:
            self.report({'ERROR'}, "Could not determine target edge")
            return {'CANCELLED'}
        
        v1 = target_edge.verts[0].co
        v2 = target_edge.verts[1].co
        new_pos_local = v1 + t * (v2 - v1)
        new_vert = bmesh.utils.edge_split(target_edge, target_edge.verts[0], t)[1]
        new_vert.co = new_pos_local
        
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        bm.select_history.clear()
        new_vert.select = True
        bm.select_history.add(new_vert)
        
        connections_created = 0
        
        if selected_vertices:
            active_vert = new_vert
            
            for v in selected_vertices:
                if v != active_vert:
                    try:
                        result = bmesh.ops.connect_vert_pair(bm, verts=[v, active_vert])
                        if result['edges']:
                            connections_created += 1
                    except:
                        try:
                            result = bmesh.ops.connect_verts(bm, verts=[v, active_vert])
                            if result['edges']:
                                connections_created += 1
                        except:
                            can_connect_directly = False
                            shared_faces = set(v.link_faces) & set(active_vert.link_faces)
                            if shared_faces:
                                can_connect_directly = True
                            
                            edge_exists = False
                            for edge in v.link_edges:
                                if active_vert in edge.verts:
                                    edge_exists = True
                                    break
                            
                            if can_connect_directly and not edge_exists:
                                bm.edges.new([v, active_vert])
                                connections_created += 1
        
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False

        new_vert.select = True
        bm.select_history.clear()
        bm.select_history.add(new_vert)
        
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'ERROR'}, "Этот оператор требует 3D-вид")
            return {'CANCELLED'}
        
        self.mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        return self.execute(context)


def menu_func(self, context):
    """Function to add items to context menu"""
    self.layout.operator(MESH_OT_add_vertex_at_cursor.bl_idname)
    self.layout.operator(MESH_OT_connect_selected_vertex_at_cursor.bl_idname)

def register():
    bpy.utils.register_class(MESH_OT_add_vertex_at_cursor)
    bpy.utils.register_class(MESH_OT_connect_selected_vertex_at_cursor)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_class(MESH_OT_add_vertex_at_cursor)
    bpy.utils.unregister_class(MESH_OT_connect_selected_vertex_at_cursor)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()