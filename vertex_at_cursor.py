import bpy
import bmesh
from mathutils import Vector
import mathutils
from bpy_extras import view3d_utils

bl_info = {
    "name": "Add Vertex at Cursor",
    "author": "eRisonv",
    "version": (1, 6),
    "blender": (2, 80, 0),
    "location": "Edit Mode > Right Click > Add Vertex at Mouse / Connect Selected Vertex at Cursor",
    "description": "Adds vertex on selected/closest edge to cursor with optional auto-connect and intersection handling",
    "category": "Mesh",
}

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
    
    def is_edge_visible_solid_mode(self, context, edge, obj, bm):
        """Simplified edge visibility check in Solid mode"""
        region = context.region
        rv3d = context.region_data
        edge_center_local = (edge.verts[0].co + edge.verts[1].co) / 2
        edge_center_world = obj.matrix_world @ edge_center_local
        view_matrix = rv3d.view_matrix
        edge_center_view = view_matrix @ edge_center_world.to_4d()
        if edge_center_view.z > 0:
            return False
        edge_faces = edge.link_faces
        if not edge_faces:
            return True
        view_location = view_matrix.inverted().translation
        for face in edge_faces:
            face_normal_world = obj.matrix_world.to_3x3() @ face.normal
            face_normal_world.normalize()
            face_center_world = obj.matrix_world @ face.calc_center_median()
            to_camera = (view_location - face_center_world).normalized()
            if face_normal_world.dot(to_camera) > 0:
                return True
        return False
    
    def find_closest_edge_to_cursor(self, context, mouse_coord, bm, obj):
        """Find closest visible edge to cursor"""
        region = context.region
        rv3d = context.region_data
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        for edge in bm.edges:
            if not self.is_edge_visible_solid_mode(context, edge, obj, bm):
                continue
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            if screen_v1 and screen_v2:
                v1_view = rv3d.view_matrix @ v1_world.to_4d()
                v2_view = rv3d.view_matrix @ v2_world.to_4d()
                if v1_view.z > 0 and v2_view.z > 0:
                    continue
                screen_edge_vec = screen_v2 - screen_v1
                screen_edge_length_sq = screen_edge_vec.length_squared
                if screen_edge_length_sq > 1e-6:
                    mouse_vec = Vector(mouse_coord)
                    to_mouse = mouse_vec - screen_v1
                    t = to_mouse.dot(screen_edge_vec) / screen_edge_length_sq
                    t_clamped = max(0.0, min(1.0, t))
                    closest_point_on_edge = screen_v1 + t_clamped * screen_edge_vec
                    distance = (mouse_vec - closest_point_on_edge).length
                    if distance < min_distance:
                        min_distance = distance
                        closest_edge = edge
                        best_t = max(0.05, min(0.95, t))
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
            region = context.region
            rv3d = context.region_data
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            if screen_v1 and screen_v2:
                screen_edge_vec = screen_v2 - screen_v1
                screen_edge_length_sq = screen_edge_vec.length_squared
                if screen_edge_length_sq > 1e-6:
                    mouse_vec = Vector(mouse_coord)
                    to_mouse = mouse_vec - screen_v1
                    t = to_mouse.dot(screen_edge_vec) / screen_edge_length_sq
                    closest_point_on_edge = screen_v1 + max(0, min(1, t)) * screen_edge_vec
                    distance_to_edge = (mouse_vec - closest_point_on_edge).length
                    if distance_to_edge > 50:
                        t = 0.5
                        self.report({'INFO'}, "Cursor far from edge - vertex added at center")
                    else:
                        t = max(0.05, min(0.95, t))
        elif is_vertex_mode:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "No suitable edges found")
                return {'CANCELLED'}
            if min_distance > 50:
                self.report({'WARNING'}, "Cursor too far from closest edge")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "No suitable edges found")
                return {'CANCELLED'}
            if min_distance > 50:
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
        
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
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
    """Add vertex on selected edge or closest to cursor edge and connect to selected vertices using topology-aware connection"""
    bl_idname = "mesh.connect_selected_vertex_at_cursor"
    bl_label = "Connect Selected Vertex at Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def is_edge_visible_solid_mode(self, context, edge, obj, bm):
        """Simplified edge visibility check in Solid mode"""
        region = context.region
        rv3d = context.region_data
        edge_center_local = (edge.verts[0].co + edge.verts[1].co) / 2
        edge_center_world = obj.matrix_world @ edge_center_local
        view_matrix = rv3d.view_matrix
        edge_center_view = view_matrix @ edge_center_world.to_4d()
        if edge_center_view.z > 0:
            return False
        edge_faces = edge.link_faces
        if not edge_faces:
            return True
        view_location = view_matrix.inverted().translation
        for face in edge_faces:
            face_normal_world = obj.matrix_world.to_3x3() @ face.normal
            face_normal_world.normalize()
            face_center_world = obj.matrix_world @ face.calc_center_median()
            to_camera = (view_location - face_center_world).normalized()
            if face_normal_world.dot(to_camera) > 0:
                return True
        return False
    
    def find_closest_edge_to_cursor(self, context, mouse_coord, bm, obj):
        """Find closest visible edge to cursor"""
        region = context.region
        rv3d = context.region_data
        closest_edge = None
        min_distance = float('inf')
        best_t = 0.5
        for edge in bm.edges:
            if not self.is_edge_visible_solid_mode(context, edge, obj, bm):
                continue
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            if screen_v1 and screen_v2:
                v1_view = rv3d.view_matrix @ v1_world.to_4d()
                v2_view = rv3d.view_matrix @ v2_world.to_4d()
                if v1_view.z > 0 and v2_view.z > 0:
                    continue
                screen_edge_vec = screen_v2 - screen_v1
                screen_edge_length_sq = screen_edge_vec.length_squared
                if screen_edge_length_sq > 1e-6:
                    mouse_vec = Vector(mouse_coord)
                    to_mouse = mouse_vec - screen_v1
                    t = to_mouse.dot(screen_edge_vec) / screen_edge_length_sq
                    t_clamped = max(0.0, min(1.0, t))
                    closest_point_on_edge = screen_v1 + t_clamped * screen_edge_vec
                    distance = (mouse_vec - closest_point_on_edge).length
                    if distance < min_distance:
                        min_distance = distance
                        closest_edge = edge
                        best_t = max(0.05, min(0.95, t))
        return closest_edge, best_t, min_distance
    
    def get_active_vert(self, bm):
        """Получить активную вершину из истории выделения"""
        if bm.select_history:
            elem = bm.select_history[-1]
            if isinstance(elem, bmesh.types.BMVert):
                return elem
        return None
    
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
        
        # Получаем выделенные вершины (может быть пустой список)
        selected_vertices = [v for v in bm.verts if v.select]
        
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
            region = context.region
            rv3d = context.region_data
            v1_world = obj.matrix_world @ target_edge.verts[0].co
            v2_world = obj.matrix_world @ target_edge.verts[1].co
            screen_v1 = view3d_utils.location_3d_to_region_2d(region, rv3d, v1_world)
            screen_v2 = view3d_utils.location_3d_to_region_2d(region, rv3d, v2_world)
            if screen_v1 and screen_v2:
                screen_edge_vec = screen_v2 - screen_v1
                screen_edge_length_sq = screen_edge_vec.length_squared
                if screen_edge_length_sq > 1e-6:
                    mouse_vec = Vector(mouse_coord)
                    to_mouse = mouse_vec - screen_v1
                    t = to_mouse.dot(screen_edge_vec) / screen_edge_length_sq
                    closest_point_on_edge = screen_v1 + max(0, min(1, t)) * screen_edge_vec
                    distance_to_edge = (mouse_vec - closest_point_on_edge).length
                    if distance_to_edge > 50:
                        t = 0.5
                        self.report({'INFO'}, "Cursor far from edge - vertex added at center")
                    else:
                        t = max(0.05, min(0.95, t))
        elif is_vertex_mode:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "No suitable edges found")
                return {'CANCELLED'}
            if min_distance > 50:
                self.report({'WARNING'}, "Cursor too far from closest edge")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        else:
            closest_edge, best_t, min_distance = self.find_closest_edge_to_cursor(context, mouse_coord, bm, obj)
            if not closest_edge:
                self.report({'ERROR'}, "No suitable edges found")
                return {'CANCELLED'}
            if min_distance > 50:
                self.report({'WARNING'}, "Cursor too far from closest edge")
                return {'CANCELLED'}
            target_edge = closest_edge
            t = best_t
        
        if not target_edge:
            self.report({'ERROR'}, "Could not determine target edge")
            return {'CANCELLED'}
        
        # Создаём новую вершину на ребре
        v1 = target_edge.verts[0].co
        v2 = target_edge.verts[1].co
        new_pos_local = v1 + t * (v2 - v1)
        new_vert = bmesh.utils.edge_split(target_edge, target_edge.verts[0], t)[1]
        new_vert.co = new_pos_local
        
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        # Устанавливаем новую вершину как активную
        bm.select_history.clear()
        new_vert.select = True
        bm.select_history.add(new_vert)
        
        connections_created = 0
        
        # Создаём соединения только если есть выделенные вершины
        if selected_vertices:
            active_vert = new_vert  # Новая вершина является активной
            
            for v in selected_vertices:
                if v != active_vert:
                    # Используем bmesh.ops.connect_vert_pair для соединения через топологию
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
                            # В крайнем случае создаём прямое соединение
                            can_connect_directly = False
                            
                            # Проверяем, находятся ли вершины на одной грани
                            shared_faces = set(v.link_faces) & set(active_vert.link_faces)
                            if shared_faces:
                                can_connect_directly = True
                            
                            # Проверяем, есть ли общие рёбра (соседние вершины)
                            edge_exists = False
                            for edge in v.link_edges:
                                if active_vert in edge.verts:
                                    edge_exists = True
                                    break
                            
                            if can_connect_directly and not edge_exists:
                                bm.edges.new([v, active_vert])
                                connections_created += 1
        
        # Обновляем lookup tables
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        # Очищаем все выделения
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False

        # Выделяем только новую вершину независимо от режима
        new_vert.select = True

        # Устанавливаем новую вершину как активную в истории выделения
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