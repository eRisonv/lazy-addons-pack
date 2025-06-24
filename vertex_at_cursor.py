bl_info = {
    "name": "Add Vertex at Cursor",
    "author": "eRisonv",
    "version": (1, 4),
    "blender": (4, 00, 0),
    "location": "Edit Mode > Right Click > Add Vertex at Mouse / Connect Selected Vertex at Cursor",
    "description": "Adds vertex on selected/closest edge to cursor with precise positioning",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector, Matrix
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

    def get_mirror_axis(self, obj):
        mirror_mod = next((mod for mod in obj.modifiers if mod.type == 'MIRROR'), None)
        if mirror_mod:
            for axis in range(3):
                if mirror_mod.use_axis[axis]:
                    return axis
        return None

    def reflect(self, co, axis):
        co_reflected = co.copy()
        co_reflected[axis] = -co_reflected[axis]
        return co_reflected

    def find_closest_visible_edge_to_cursor(self, context, mouse_coord, bm, obj):
        region = context.region
        rv3d = context.region_data
        
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)
        
        mirror_axis = self.get_mirror_axis(obj)
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        
        for edge in bm.edges:
            v1 = obj.matrix_world @ edge.verts[0].co
            v2 = obj.matrix_world @ edge.verts[1].co
            distance_3d, t_3d, point_on_line = self.ray_to_line_closest_points(ray_origin, ray_direction, v1, v2)
            screen_point = view3d_utils.location_3d_to_region_2d(region, rv3d, point_on_line)
            if screen_point:
                cursor_vec = Vector(mouse_coord)
                distance_screen = (cursor_vec - screen_point).length
            else:
                distance_screen = float('inf')
            
            if mirror_axis is not None:
                v1_m = obj.matrix_world @ self.reflect(edge.verts[0].co, mirror_axis)
                v2_m = obj.matrix_world @ self.reflect(edge.verts[1].co, mirror_axis)
                distance_3d_m, t_3d_m, point_on_line_m = self.ray_to_line_closest_points(ray_origin, ray_direction, v1_m, v2_m)
                screen_point_m = view3d_utils.location_3d_to_region_2d(region, rv3d, point_on_line_m)
                if screen_point_m:
                    distance_screen_m = (cursor_vec - screen_point_m).length
                else:
                    distance_screen_m = float('inf')
            else:
                distance_screen_m = float('inf')
            
            if distance_screen < distance_screen_m:
                candidate_distance = distance_screen
                candidate_t = t_3d
            else:
                candidate_distance = distance_screen_m
                candidate_t = t_3d_m
            
            if candidate_distance < min_distance:
                min_distance = candidate_distance
                closest_edge = edge
                best_t = candidate_t
        
        if closest_edge and min_distance < 100:
            return closest_edge, best_t, min_distance
        else:
            return None, 0.5, float('inf')

    def execute(self, context):
        obj = context.active_object
        mouse_coord = getattr(self, 'mouse_coord', None)
        if not mouse_coord:
            self.report({'WARNING'}, "Не удалось определить позицию курсора")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        select_mode = context.tool_settings.mesh_select_mode
        is_edge_mode = select_mode[1]
        
        target_edge = None
        t = 0.5
        
        if is_edge_mode:
            selected_edges = [edge for edge in bm.edges if edge.select]
            if not selected_edges:
                self.report({'ERROR'}, "Ребро не выбрано")
                return {'CANCELLED'}
            if len(selected_edges) > 1:
                self.report({'ERROR'}, "Выберите только одно ребро")
                return {'CANCELLED'}
            
            target_edge = selected_edges[0]
            
            region = context.region
            rv3d = context.region_data
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if screen_v1 and screen_v2:
                edge_vec = screen_v2 - screen_v1
                edge_len_sq = edge_vec.length_squared
                
                if edge_len_sq > 1e-6:
                    cursor_vec = Vector(mouse_coord)
                    point_vec = cursor_vec - screen_v1
                    t = max(0.0, min(1.0, point_vec.dot(edge_vec) / edge_len_sq))
                    
                    closest_point = screen_v1 + t * edge_vec
                    cursor_distance = (cursor_vec - closest_point).length
                    if cursor_distance > 50:
                        t = 0.5
                        self.report({'INFO'}, "Курсор далеко от ребра - вершина добавлена в центр")
                    else:
                        t = max(0.05, min(0.95, t))
                else:
                    t = 0.5
            else:
                t = 0.5
        else:
            closest_edge, best_t, min_distance = self.find_closest_visible_edge_to_cursor(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "Подходящее ребро не найдено")
                return {'CANCELLED'}
            if min_distance > 100:
                self.report({'WARNING'}, "Курсор слишком далеко от ближайшего ребра")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        
        if not target_edge:
            self.report({'ERROR'}, "Не удалось определить целевое ребро")
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
        
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        if select_mode[0]:
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
    """Add vertex on selected edge or closest to cursor edge and connect to selected vertices, or connect to vertex under cursor"""
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
    
    def is_vertex_visible(self, context, vert, obj, bm):
        """Проверяет, видима ли вершина"""
        region = context.region
        rv3d = context.region_data
        vert_world = obj.matrix_world @ vert.co
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (region.width/2, region.height/2))
        ray_direction = (vert_world - ray_origin).normalized()
        distance = (vert_world - ray_origin).length
        success, hit_location, _, _ = obj.ray_cast(ray_origin, ray_direction, distance=distance)
        if not success:
            return True
        distance_to_hit = (hit_location - ray_origin).length
        return distance_to_hit >= distance - 0.001
    
    def find_vertex_under_cursor(self, context, mouse_coord, bm, obj, tolerance=35):
        """Находит вершину под курсором, включая зеркальные вершины от модификатора Mirror"""
        region = context.region
        rv3d = context.region_data
        camera_pos = view3d_utils.region_2d_to_origin_3d(region, rv3d, (region.width/2, region.height/2))
        
        closest_vertex = None
        min_distance = float('inf')
        
        # Получаем ось отражения, если есть модификатор Mirror
        mirror_axis = self.get_mirror_axis(obj)
        
        for vert in bm.verts:
            if not self.is_vertex_visible(context, vert, obj, bm):
                continue
            
            # Проверяем оригинальную вершину
            vert_world = obj.matrix_world @ vert.co
            screen_coord = view3d_utils.location_3d_to_region_2d(region, rv3d, vert_world)
            
            if screen_coord:
                screen_dist = (Vector(mouse_coord) - screen_coord).length
                if screen_dist < tolerance and screen_dist < min_distance:
                    is_front_vertex = False
                    for face in vert.link_faces:
                        normal_world = (obj.matrix_world.to_3x3() @ face.normal).normalized()
                        face_center_world = obj.matrix_world @ face.calc_center_median()
                        view_dir = (camera_pos - face_center_world).normalized()
                        if normal_world.dot(view_dir) > 0:
                            is_front_vertex = True
                            break
                    if is_front_vertex:
                        min_distance = screen_dist
                        closest_vertex = vert
            
            # Проверяем зеркальную вершину, если есть модификатор Mirror
            if mirror_axis is not None:
                vert_mirrored = self.reflect(vert.co, mirror_axis)
                vert_mirrored_world = obj.matrix_world @ vert_mirrored
                screen_coord_mirrored = view3d_utils.location_3d_to_region_2d(region, rv3d, vert_mirrored_world)
                
                if screen_coord_mirrored:
                    screen_dist_mirrored = (Vector(mouse_coord) - screen_coord_mirrored).length
                    if screen_dist_mirrored < tolerance and screen_dist_mirrored < min_distance:
                        # Используем оригинальную вершину, если курсор над зеркальной
                        is_front_vertex = False
                        for face in vert.link_faces:
                            normal_world = (obj.matrix_world.to_3x3() @ face.normal).normalized()
                            face_center_world = obj.matrix_world @ face.calc_center_median()
                            view_dir = (camera_pos - face_center_world).normalized()
                            if normal_world.dot(view_dir) > 0:
                                is_front_vertex = True
                                break
                        if is_front_vertex:
                            min_distance = screen_dist_mirrored
                            closest_vertex = vert
        
        return closest_vertex, min_distance

    def get_mirror_axis(self, obj):
        """Получает ось отражения для модификатора Mirror"""
        mirror_mod = next((mod for mod in obj.modifiers if mod.type == 'MIRROR'), None)
        if mirror_mod:
            for axis in range(3):
                if mirror_mod.use_axis[axis]:
                    return axis
        return None

    def reflect(self, co, axis):
        """Отражает координаты по указанной оси"""
        co_reflected = co.copy()
        co_reflected[axis] = -co_reflected[axis]
        return co_reflected

    def find_closest_edge_to_cursor_knife_style(self, context, mouse_coord, bm, obj):
        """Находит ближайшее ребро к курсору, учитывая модификатор Mirror"""
        region = context.region
        rv3d = context.region_data
        
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)
        
        mirror_axis = self.get_mirror_axis(obj)
        
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        
        cursor_vec = Vector(mouse_coord)
        
        for edge in bm.edges:
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            distance_3d, t_3d, point_on_line = self.ray_to_line_closest_points(ray_origin, ray_direction, v1_world, v2_world)
            screen_point = view3d_utils.location_3d_to_region_2d(region, rv3d, point_on_line)
            if screen_point:
                distance_screen = (cursor_vec - screen_point).length
            else:
                distance_screen = float('inf')
            
            if mirror_axis is not None:
                v1_m = obj.matrix_world @ self.reflect(edge.verts[0].co, mirror_axis)
                v2_m = obj.matrix_world @ self.reflect(edge.verts[1].co, mirror_axis)
                distance_3d_m, t_3d_m, point_on_line_m = self.ray_to_line_closest_points(ray_origin, ray_direction, v1_m, v2_m)
                screen_point_m = view3d_utils.location_3d_to_region_2d(region, rv3d, point_on_line_m)
                if screen_point_m:
                    distance_screen_m = (cursor_vec - screen_point_m).length
                else:
                    distance_screen_m = float('inf')
            else:
                distance_screen_m = float('inf')
            
            if distance_screen < distance_screen_m:
                candidate_distance = distance_screen
                candidate_t = t_3d
            else:
                candidate_distance = distance_screen_m
                candidate_t = t_3d_m
            
            if candidate_distance < min_distance:
                min_distance = candidate_distance
                closest_edge = edge
                best_t = candidate_t
        
        if closest_edge and min_distance < 100:
            return closest_edge, best_t, min_distance
        else:
            return None, 0.5, float('inf')

    def execute(self, context):
        obj = context.active_object
        mouse_coord = getattr(self, 'mouse_coord', None)
        if not mouse_coord:
            self.report({'WARNING'}, "Не удалось определить позицию курсора")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        selected_vertices = [v for v in bm.verts if v.select]
        
        # Проверяем, есть ли вершина под курсором
        vertex_under_cursor, cursor_distance = self.find_vertex_under_cursor(context, mouse_coord, bm, obj, tolerance=35)
        if not vertex_under_cursor:
            vertex_under_cursor, cursor_distance = self.find_vertex_under_cursor(context, mouse_coord, bm, obj, tolerance=20)
        
        # Если выбрано 2+ вершин и под курсором есть вершина
        if len(selected_vertices) >= 2 and vertex_under_cursor:
            connections_created = 0
            
            for selected_vert in selected_vertices:
                if selected_vert == vertex_under_cursor:
                    continue
                
                edge_exists = False
                for edge in selected_vert.link_edges:
                    if vertex_under_cursor in edge.verts:
                        edge_exists = True
                        break
                
                if not edge_exists:
                    try:
                        result = bmesh.ops.connect_vert_pair(bm, verts=[selected_vert, vertex_under_cursor])
                        if result.get('edges'):
                            connections_created += 1
                    except:
                        try:
                            result = bmesh.ops.connect_verts(bm, verts=[selected_vert, vertex_under_cursor])
                            if result.get('edges'):
                                connections_created += 1
                        except:
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
                self.report({'WARNING'}, "Не удалось создать новые соединения")
            
            return {'FINISHED'}
        
        # Если выбрана 1 вершина и под курсором другая вершина
        elif len(selected_vertices) == 1 and vertex_under_cursor and vertex_under_cursor != selected_vertices[0]:
            selected_vert = selected_vertices[0]
            
            edge_exists = False
            for edge in selected_vert.link_edges:
                if vertex_under_cursor in edge.verts:
                    edge_exists = True
                    break
            
            if not edge_exists:
                try:
                    result = bmesh.ops.connect_vert_pair(bm, verts=[selected_vert, vertex_under_cursor])
                    connections_created = 1 if result.get('edges') else 0
                except:
                    try:
                        result = bmesh.ops.connect_verts(bm, verts=[selected_vert, vertex_under_cursor])
                        connections_created = 1 if result.get('edges') else 0
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
                self.report({'INFO'}, "Вершины уже соединены")
                return {'FINISHED'}
        
        # Если вершины под курсором нет, продолжаем как раньше
        select_mode = context.tool_settings.mesh_select_mode
        is_edge_mode = select_mode[1]
        
        target_edge = None
        t = 0.5
        
        if is_edge_mode:
            selected_edges = [edge for edge in bm.edges if edge.select]
            if not selected_edges:
                self.report({'ERROR'}, "Ребро не выбрано")
                return {'CANCELLED'}
            if len(selected_edges) > 1:
                self.report({'ERROR'}, "Выберите только одно ребро")
                return {'CANCELLED'}
            
            target_edge = selected_edges[0]
            
            region = context.region
            rv3d = context.region_data
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            
            if screen_v1 and screen_v2:
                edge_vec = screen_v2 - screen_v1
                edge_len_sq = edge_vec.length_squared
                
                if edge_len_sq > 1e-6:
                    cursor_vec = Vector(mouse_coord)
                    point_vec = cursor_vec - screen_v1
                    t = max(0.0, min(1.0, point_vec.dot(edge_vec) / edge_len_sq))
                    
                    closest_point = screen_v1 + t * edge_vec
                    cursor_distance = (cursor_vec - closest_point).length
                    if cursor_distance > 50:
                        t = 0.5
                        self.report({'INFO'}, "Курсор далеко от ребра - вершина добавлена в центр")
                    else:
                        t = max(0.05, min(0.95, t))
                else:
                    t = 0.5
            else:
                t = 0.5
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor_knife_style(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "Подходящее ребро не найдено")
                return {'CANCELLED'}
            if min_distance > 100:
                self.report({'WARNING'}, "Курсор слишком далеко от ближайшего ребра")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        
        if not target_edge:
            self.report({'ERROR'}, "Не удалось определить целевое ребро")
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