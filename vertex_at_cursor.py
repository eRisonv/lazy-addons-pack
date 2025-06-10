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
    
    def is_edge_visible_improved(self, context, edge, obj, bm):
        """Улучшенная проверка видимости ребра"""
        region = context.region
        rv3d = context.region_data
        
        # Проверяем оба конца ребра
        v1_world = obj.matrix_world @ edge.verts[0].co
        v2_world = obj.matrix_world @ edge.verts[1].co
        
        # Проверяем, находятся ли вершины за камерой
        v1_view = rv3d.view_matrix @ v1_world.to_4d()
        v2_view = rv3d.view_matrix @ v2_world.to_4d()
        
        # Если обе вершины за камерой, ребро не видно
        if v1_view.z > 0 and v2_view.z > 0:
            return False
        
        # Проверяем проекцию на экран
        screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
        screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
        
        if not screen_v1 or not screen_v2:
            return False
        
        # Проверяем, находится ли ребро в пределах видимой области
        region_width = region.width
        region_height = region.height
        
        # Расширяем границы для более мягкой проверки
        margin = 50
        if (max(screen_v1.x, screen_v2.x) < -margin or 
            min(screen_v1.x, screen_v2.x) > region_width + margin or
            max(screen_v1.y, screen_v2.y) < -margin or 
            min(screen_v1.y, screen_v2.y) > region_height + margin):
            return False
        
        # Проверяем видимость с помощью нормалей граней
        edge_faces = edge.link_faces
        if not edge_faces:
            return True  # Boundary edge - всегда видно
        
        view_location = rv3d.view_matrix.inverted().translation
        visible_faces = 0
        
        for face in edge_faces:
            face_normal_world = obj.matrix_world.to_3x3() @ face.normal
            face_normal_world.normalize()
            face_center_world = obj.matrix_world @ face.calc_center_median()
            to_camera = (view_location - face_center_world).normalized()
            
            # Если нормаль грани направлена к камере, грань видна
            if face_normal_world.dot(to_camera) > -0.1:  # Небольшая толерантность
                visible_faces += 1
        
        return visible_faces > 0
    
    def find_closest_edge_to_cursor_improved(self, context, mouse_coord, bm, obj):
        """Улучшенный поиск ближайшего ребра к курсору с использованием 3D лучей"""
        ray_origin, ray_direction = self.cast_ray_from_cursor(context, mouse_coord)
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        best_intersection_point = None
        
        for edge in bm.edges:
            if not self.is_edge_visible_improved(context, edge, obj, bm):
                continue
            
            # Переводим вершины ребра в мировые координаты
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            
            # Находим ближайшие точки между лучом и ребром
            distance, t_line, point_on_line = self.ray_to_line_closest_points(
                ray_origin, ray_direction, v1_world, v2_world
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_edge = edge
                best_t = max(0.05, min(0.95, t_line))  # Отступ от краёв
                best_intersection_point = point_on_line
        
        return closest_edge, best_t, min_distance
    
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
            
            # Используем улучшенный метод позиционирования даже для выделенного ребра
            ray_origin, ray_direction = self.cast_ray_from_cursor(context, mouse_coord)
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            
            distance, t_line, point_on_line = self.ray_to_line_closest_points(
                ray_origin, ray_direction, v1_world, v2_world
            )
            
            # Проверяем, достаточно ли близко курсор к ребру
            region = context.region
            rv3d = context.region_data
            screen_point = view3d_utils.location_3d_to_region_2d(region, rv3d, point_on_line)
            
            if screen_point:
                cursor_distance = (Vector(mouse_coord) - screen_point).length
                if cursor_distance > 50:
                    t = 0.5
                    self.report({'INFO'}, "Cursor far from edge - vertex added at center")
                else:
                    t = max(0.05, min(0.95, t_line))
            else:
                t = 0.5
                
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor_improved(context, mouse_coord, bm, obj)
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
        """Проверяет, виден ли вертекс на основе видимости его связных граней"""
        region = context.region
        rv3d = context.region_data
        view_location = rv3d.view_matrix.inverted().translation
        
        for face in vert.link_faces:
            face_normal_world = obj.matrix_world.to_3x3() @ face.normal
            face_normal_world.normalize()
            face_center_world = obj.matrix_world @ face.calc_center_median()
            to_camera = (view_location - face_center_world).normalized()
            
            if face_normal_world.dot(to_camera) > -0.1:  # Небольшая толерантность
                return True
        return False
    
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
    
    def is_edge_visible_improved(self, context, edge, obj, bm):
        """Улучшенная проверка видимости ребра"""
        region = context.region
        rv3d = context.region_data
        
        v1_world = obj.matrix_world @ edge.verts[0].co
        v2_world = obj.matrix_world @ edge.verts[1].co
        
        v1_view = rv3d.view_matrix @ v1_world.to_4d()
        v2_view = rv3d.view_matrix @ v2_world.to_4d()
        
        if v1_view.z > 0 and v2_view.z > 0:
            return False
        
        screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
        screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
        
        if not screen_v1 or not screen_v2:
            return False
        
        edge_faces = edge.link_faces
        if not edge_faces:
            return True
        
        view_location = rv3d.view_matrix.inverted().translation
        visible_faces = 0
        
        for face in edge_faces:
            face_normal_world = obj.matrix_world.to_3x3() @ face.normal
            face_normal_world.normalize()
            face_center_world = obj.matrix_world @ face.calc_center_median()
            to_camera = (view_location - face_center_world).normalized()
            
            if face_normal_world.dot(to_camera) > -0.1:
                visible_faces += 1
        
        return visible_faces > 0
    
    def find_closest_edge_to_cursor_improved(self, context, mouse_coord, bm, obj):
        """Улучшенный поиск ближайшего ребра к курсору"""
        ray_origin, ray_direction = self.cast_ray_from_cursor(context, mouse_coord)
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        
        for edge in bm.edges:
            if not self.is_edge_visible_improved(context, edge, obj, bm):
                continue
            
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            
            distance, t_line, point_on_line = self.ray_to_line_closest_points(
                ray_origin, ray_direction, v1_world, v2_world
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_edge = edge
                best_t = max(0.05, min(0.95, t_line))
        
        return closest_edge, best_t, min_distance
    
    def find_vertex_under_cursor(self, context, mouse_coord, bm, obj, tolerance=30):
        """Находит любой видимый вертекс под курсором в пределах толерантности (включая выделенные)"""
        region = context.region
        rv3d = context.region_data
        mouse_vec = Vector(mouse_coord)
        closest_vertex = None
        min_distance = float('inf')
        
        for vert in bm.verts:
            # Пропускаем только невидимые вертексы
            if not self.is_vertex_visible(context, vert, obj, bm):
                continue
                
            vert_world = obj.matrix_world @ vert.co
            vert_view = rv3d.view_matrix @ vert_world.to_4d()
            
            # Пропускаем вертексы за камерой
            if vert_view.z > 0:
                continue
                
            screen_coord = view3d_utils.location_3d_to_region_2d(region, rv3d, vert_world)
            if screen_coord:
                distance = (mouse_vec - screen_coord).length
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
        
        # Сначала ищем вертекс под курсором с повышенным приоритетом
        vertex_under_cursor, cursor_distance = self.find_vertex_under_cursor(context, mouse_coord, bm, obj, tolerance=35)
        
        # Если не нашли вертекс рядом, пробуем с меньшей толерантностью но более точно
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
                                # Ребро уже существует или другая ошибка
                                pass
            
            # Обновляем таблицы после создания соединений
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.normal_update()
            
            # Очищаем выделение и выделяем только целевой вертекс
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
            
            if connections_created > 0:
                self.report({'INFO'}, f"Connected {connections_created} vertices to target vertex")
            else:
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
                
                if connections_created > 0:
                    self.report({'INFO'}, "Connected vertices")
                else:
                    self.report({'WARNING'}, "Could not create connection")
                
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "Vertices are already connected")
                return {'FINISHED'}
        
        # Основная логика создания вертекса на ребре (если не было соединения вертексов)
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
            
            ray_origin, ray_direction = self.cast_ray_from_cursor(context, mouse_coord)
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            
            distance, t_line, point_on_line = self.ray_to_line_closest_points(
                ray_origin, ray_direction, v1_world, v2_world
            )
            
            region = context.region
            rv3d = context.region_data
            screen_point = view3d_utils.location_3d_to_region_2d(region, rv3d, point_on_line)
            
            if screen_point:
                cursor_distance = (Vector(mouse_coord) - screen_point).length
                if cursor_distance > 50:
                    t = 0.5
                    self.report({'INFO'}, "Cursor far from edge - vertex added at center")
                else:
                    t = max(0.05, min(0.95, t_line))
            else:
                t = 0.5
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor_improved(context, mouse_coord, bm, obj)
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