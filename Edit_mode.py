bl_info = {
    "name": "Edit Mode Display",
    "author": "eRisonv",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Viewport Overlays",
    "description": "Shows current edit mode in viewport",
    "category": "3D View",
}

import bpy
import blf
import time
from bpy.types import (Panel, AddonPreferences, PropertyGroup)
from bpy.props import (FloatProperty, EnumProperty, FloatVectorProperty, PointerProperty, BoolProperty)
from bpy.app.handlers import persistent

# Глобальные переменные для анимации
class AnimationState:
    def __init__(self):
        self.start_time = 0
        self.is_active = False
        self.target_mode = None
        self.current_opacity = 0
        self.target_opacity = 0
        self.last_mode = None
        self.last_update_time = 0  # Добавляем отслеживание времени последнего обновления
        
animation_state = AnimationState()
_handle = None
_is_handler_active = False
_timer = None

class EMDSettings(PropertyGroup):
    is_enabled: BoolProperty(
        name="Enable Display",
        description="Enable edit mode display",
        default=True
    )

position_items = [
    ('TOP_CENTER', "Сверху по центру", "Разместить текст вверху по центру"),
    ('BOTTOM_CENTER', "Снизу по центру", "Разместить текст внизу по центру"),
]

def get_animation_parameters():
    return {
        'FADE_IN_DURATION': 0.1,
        'DISPLAY_DURATION': 0.5,
        'FADE_OUT_DURATION': 0.2
    }

def limit_redraw_rate():
    global _last_redraw_time
    current_time = time.time()
    if current_time - _last_redraw_time < 0.016:  # Примерно 60 FPS
        return True
    _last_redraw_time = current_time
    return False

class EMD_OT_modal_timer(bpy.types.Operator):
    bl_idname = "emd.modal_timer"
    bl_label = "Mode Display Animation Timer"
    
    _timer = None
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            if not animation_state.is_active:
                self.cancel(context)
                return {'CANCELLED'}
                
            params = get_animation_parameters()
            total_duration = params['FADE_IN_DURATION'] + params['DISPLAY_DURATION'] + params['FADE_OUT_DURATION']
            elapsed_time = time.time() - animation_state.start_time
            
            # Плавный переход opacity
            prefs = context.preferences.addons[__name__].preferences
            if elapsed_time < params['FADE_IN_DURATION']:
                animation_state.current_opacity = (elapsed_time / params['FADE_IN_DURATION']) * prefs.opacity
            elif elapsed_time < (params['FADE_IN_DURATION'] + params['DISPLAY_DURATION']):
                animation_state.current_opacity = prefs.opacity
            else:
                remaining_time = total_duration - elapsed_time
                if remaining_time > 0:
                    animation_state.current_opacity = (remaining_time / params['FADE_OUT_DURATION']) * prefs.opacity
                else:
                    animation_state.current_opacity = 0
                    animation_state.is_active = False
            
            # Запрос перерисовки всех 3D областей
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.016, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

class EditModeDisplayPreferences(AddonPreferences):
    bl_idname = __name__

    opacity: FloatProperty(
        name="Прозрачность",
        description="Настройка прозрачности текста",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR'
    )
    
    scale: FloatProperty(
        name="Масштаб",
        description="Настройка размера текста",
        default=1.3,
        min=0.5,
        max=2.0,
        subtype='FACTOR'
    )
    
    position: EnumProperty(
        name="Позиция",
        description="Выберите позицию текста",
        items=position_items,
        default='TOP_CENTER'
    )

    vertex_color: FloatVectorProperty(
        name="VERTEX",
        description="Цвет для режима вершин",
        subtype='COLOR',
        default=(0/255, 255/255, 32/255),
        min=0.0,
        max=1.0
    )

    edge_color: FloatVectorProperty(
        name="EDGE",
        description="Цвет для режима рёбер",
        subtype='COLOR',
        default=(255/255, 253/255, 0/255),
        min=0.0,
        max=1.0
    )

    face_color: FloatVectorProperty(
        name="FACE",
        description="Цвет для режима граней",
        subtype='COLOR',
        default=(255/255, 172/255, 0/255),
        min=0.0,
        max=1.0
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Основные настройки:")
        box.prop(self, "opacity")
        box.prop(self, "scale")
        box.prop(self, "position")
        
        color_box = layout.box()
        color_box.label(text="Настройки цветов:")
        color_box.prop(self, "vertex_color")
        color_box.prop(self, "edge_color")
        color_box.prop(self, "face_color")

def get_mode_color(context, mode):
    prefs = context.preferences.addons[__name__].preferences
    color_map = {
        'VERTEX': prefs.vertex_color,
        'EDGE': prefs.edge_color,
        'FACE': prefs.face_color
    }
    return color_map.get(mode, (1, 1, 1))

def get_current_mode(context):
    obj = context.active_object
    if obj is None or obj.mode != 'EDIT' or obj.type != 'MESH':
        return None
    
    tool_settings = context.tool_settings
    
    # Проверка активного инструмента
    active_tool = None
    try:
        if hasattr(context.workspace, 'tools'):
            active_tool = context.workspace.tools.from_space_view3d_mode(context.mode).idname
    except Exception:
        pass
    
    # Специальная обработка для nFlow и подобных инструментов
    if active_tool and ('nflow' in active_tool.lower() or 'nsolve' in active_tool.lower()):
        return animation_state.last_mode or "VERTEX"
    
    # Строгая проверка режимов выделения
    select_modes = (
        tool_settings.mesh_select_mode[0], 
        tool_settings.mesh_select_mode[1], 
        tool_settings.mesh_select_mode[2]
    )
   
    
    # Приоритетное определение режима
    if select_modes[0] is True and select_modes[1] is False and select_modes[2] is False:
        return "VERTEX"
    elif select_modes[0] is False and select_modes[1] is True and select_modes[2] is False:
        return "EDGE"
    elif select_modes[0] is False and select_modes[1] is False and select_modes[2] is True:
        return "FACE"
    
    # Последний шанс - используем последний известный режим
    return animation_state.last_mode or "VERTEX"

def start_animation():
    global animation_start_time, is_animating
    animation_start_time = time.time()
    is_animating = True
    bpy.ops.emd.modal_timer('INVOKE_DEFAULT')
    
def start_animation(context, new_mode):
    # Финальная проверка режима перед анимацией
    tool_settings = context.tool_settings
    current_select_modes = (
        tool_settings.mesh_select_mode[0], 
        tool_settings.mesh_select_mode[1], 
        tool_settings.mesh_select_mode[2]
    )
   
    
    # Проверка активного инструмента
    active_tool = None
    try:
        if hasattr(context.workspace, 'tools'):
            active_tool = context.workspace.tools.from_space_view3d_mode(context.mode).idname
    except Exception:
        pass
    
    # Игнорируем анимацию при специальных инструментах
    if active_tool and ('nflow' in active_tool.lower() or 'nsolve' in active_tool.lower()):
        return
    
    # Продолжаем с оригинальной логикой
    animation_state.start_time = time.time()
    animation_state.is_active = True
    animation_state.target_mode = new_mode
    animation_state.current_opacity = 0
    animation_state.target_opacity = context.preferences.addons[__name__].preferences.opacity
    
    # Запуск таймера только если он еще не активен
    if not EMD_OT_modal_timer._timer:
        bpy.ops.emd.modal_timer('INVOKE_DEFAULT')

def get_animation_opacity(context):
    elapsed_time = time.time() - animation_start_time
    prefs = context.preferences.addons[__name__].preferences
    
    FADE_IN_DURATION = 0.1
    DISPLAY_DURATION = 0.8
    FADE_OUT_DURATION = 0.2
    TOTAL_DURATION = FADE_IN_DURATION + DISPLAY_DURATION + FADE_OUT_DURATION
    
    if elapsed_time >= TOTAL_DURATION:
        global is_animating
        is_animating = False
        return 0
    
    if elapsed_time < FADE_IN_DURATION:
        return (elapsed_time / FADE_IN_DURATION) * prefs.opacity
    elif elapsed_time < (FADE_IN_DURATION + DISPLAY_DURATION):
        return prefs.opacity
    else:
        fade_progress = (elapsed_time - FADE_IN_DURATION - DISPLAY_DURATION) / FADE_OUT_DURATION
        return (1 - fade_progress) * prefs.opacity

def draw_callback_px():
    try:
        context = bpy.context
        if not context.scene.emd_settings.is_enabled and not animation_state.is_active:
            return
            
        if animation_state.current_opacity <= 0:
            return
        
        current_mode = animation_state.target_mode
        if not current_mode:
            return
        
        prefs = context.preferences.addons[__name__].preferences
        font_id = 0
        font_size = int(24 * prefs.scale)
        
        blf.size(font_id, font_size)
        text_width, text_height = blf.dimensions(font_id, current_mode)
        
        area = context.area
        x = area.width / 2 - text_width / 2
        y = 60 if prefs.position == 'BOTTOM_CENTER' else area.height - 60
        
        color = get_mode_color(context, current_mode)
        
        # Отрисовка с текущей opacity из animation_state
        outline_color = (0, 0, 0, animation_state.current_opacity)
        text_color = (*color, animation_state.current_opacity)
        
        # Контур
        blf.color(font_id, *outline_color)
        for dx, dy in ((-1,-1), (-1,1), (1,-1), (1,1)):
            blf.position(font_id, x + dx, y + dy, 0)
            blf.draw(font_id, current_mode)
        
        # Основной текст
        blf.color(font_id, *text_color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, current_mode)
        
    except:
        pass

@persistent
def get_current_mode(context):
    obj = context.active_object
    if obj is None or obj.mode != 'EDIT' or obj.type != 'MESH':
        return None
    
    tool_settings = context.tool_settings
    
    # Приоритетное определение режима с принудительной проверкой
    if tool_settings.mesh_select_mode[0] is True and tool_settings.mesh_select_mode[1] is False and tool_settings.mesh_select_mode[2] is False:
        return "VERTEX"
    elif tool_settings.mesh_select_mode[0] is False and tool_settings.mesh_select_mode[1] is True and tool_settings.mesh_select_mode[2] is False:
        return "EDGE"
    elif tool_settings.mesh_select_mode[0] is False and tool_settings.mesh_select_mode[1] is False and tool_settings.mesh_select_mode[2] is True:
        return "FACE"
    
    # Последний шанс - используем последний известный режим
    return animation_state.last_mode or "VERTEX"

@persistent
def mode_update_handler(scene):
    if not bpy.context.active_object:
        return
        
    current_time = time.time()
    # Увеличиваем порог игнорирования частых обновлений
    if current_time - animation_state.last_update_time < 0.1:  # 100мс
        return
        
    current_mode = get_current_mode(bpy.context)
    
    # Более строгая проверка изменения режима
    if (current_mode and 
        current_mode != animation_state.last_mode and 
        current_mode != animation_state.target_mode):
        animation_state.last_mode = current_mode
        start_animation(bpy.context, current_mode)
        animation_state.last_update_time = current_time

class EMD_OT_toggle_display(bpy.types.Operator):
    bl_idname = "emd.toggle_display"
    bl_label = "Toggle Mode Display"
    
    def execute(self, context):
        context.scene.emd_settings.is_enabled = not context.scene.emd_settings.is_enabled
        if context.scene.emd_settings.is_enabled:
            start_animation()
        return {'FINISHED'}
        
def is_nsolve_active(context):
    """Проверяет, активен ли инструмент nSolve"""
    if hasattr(context.workspace, 'tools'):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode)
        if active_tool:
            return 'nsolve' in active_tool.idname.lower()
    return False

class EMD_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_parent_id = 'VIEW3D_PT_overlay'
    bl_label = "Mode Display"
    
    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.emd_settings, "is_enabled", text="Show Mode")

def ensure_handler_status():
    global _handle, _is_handler_active
    if _handle is None and not _is_handler_active:
        _handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')
        _is_handler_active = True

@persistent
def load_handler(dummy):
    ensure_handler_status()

def register():
    bpy.utils.register_class(EMDSettings)
    bpy.utils.register_class(EMD_OT_modal_timer)
    bpy.utils.register_class(EditModeDisplayPreferences)
    bpy.utils.register_class(EMD_OT_toggle_display)
    bpy.utils.register_class(EMD_PT_panel)
    
    bpy.types.Scene.emd_settings = PointerProperty(type=EMDSettings)
    
    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.depsgraph_update_post.append(mode_update_handler)
    
    ensure_handler_status()
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        km.keymap_items.new(
            "emd.toggle_display",
            type='M',
            value='PRESS',
            ctrl=True
        )

def unregister():
    global _handle, _is_handler_active
    
    bpy.app.handlers.load_post.remove(load_handler)
    if mode_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(mode_update_handler)
    
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
        _handle = None
        _is_handler_active = False
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.get('3D View')
        if km:
            for kmi in km.keymap_items:
                if kmi.idname == "emd.toggle_display":
                    km.keymap_items.remove(kmi)
    
    bpy.utils.unregister_class(EMD_PT_panel)
    bpy.utils.unregister_class(EMD_OT_toggle_display)
    bpy.utils.unregister_class(EditModeDisplayPreferences)
    bpy.utils.unregister_class(EMD_OT_modal_timer)
    bpy.utils.unregister_class(EMDSettings)
    
    del bpy.types.Scene.emd_settings

if __name__ == "__main__":
    register