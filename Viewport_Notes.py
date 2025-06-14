bl_info = {
    "name": "Viewport Notes",
    "author": "eRisonv",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "View3D > Viewport Overlays, Shortcut: Ctrl+Q",
    "description": "Shows custom notes in viewport with support for Sculpt Mode",
    "category": "3D View",
}

import bpy
import blf
import json
import os
from bpy.types import (Panel, AddonPreferences, PropertyGroup, Operator)
from bpy.props import (StringProperty, FloatProperty, EnumProperty, CollectionProperty, BoolProperty, PointerProperty)

# Глобальный словарь для хранения состояния видимости по областям
viewport_notes_show_per_area = {}

def get_settings_path():
    user_path = bpy.utils.user_resource('CONFIG')
    return os.path.join(user_path, "viewport_notes_settings.json")

def save_settings():
    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
        settings = {
            'modeling_lines': [line.text for line in prefs.modeling_lines],
            'sculpt_lines': [line.text for line in prefs.sculpt_lines],
            'opacity': prefs.opacity,
            'scale': prefs.scale,
            'position': prefs.position,
            'show_notes': bpy.context.window_manager.viewport_notes_show,
            'show_scale': prefs.show_scale,
            'use_mode_switching': prefs.use_mode_switching,
            'modeling_expanded': prefs.modeling_expanded,
            'sculpt_expanded': prefs.sculpt_expanded,
            'use_hotkey': prefs.use_hotkey,
            'hide_scale_on_hotkey': prefs.hide_scale_on_hotkey
        }
        
        settings_path = get_settings_path()
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_settings():
    settings_path = get_settings_path()
    if not os.path.exists(settings_path):
        return None
        
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# Список позиций для текста
position_items = [
    ('TOP_LEFT', "Левый верхний", "Разместить текст в левом верхнем углу"),
    ('TOP_RIGHT', "Правый верхний", "Разместить текст в правом верхнем углу"),
    ('BOTTOM_LEFT', "Нижний левый", "Разместить текст в нижнем левом углу"),
    ('BOTTOM_RIGHT', "Нижний правый", "Разместить текст в нижнем правом углу"),
]

class NoteLine(PropertyGroup):
    text: StringProperty(
        name="Text",
        description="Text line",
        default="",
        update=lambda self, context: save_settings()
    )

class AddLineOperator(Operator):
    bl_idname = "viewport_notes.add_line"
    bl_label = "Add New Line"
    bl_description = "Add a new text line"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: StringProperty(default="modeling")
    
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        
        if self.mode == "sculpt":
            line = prefs.sculpt_lines.add()
        else:  # modeling
            line = prefs.modeling_lines.add()
            
        line.text = ""
        save_settings()
        return {'FINISHED'}

class RemoveLineOperator(Operator):
    bl_idname = "viewport_notes.remove_line"
    bl_label = "Remove Line"
    bl_description = "Remove this text line"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: bpy.props.IntProperty()
    mode: StringProperty(default="modeling")
    
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        
        if self.mode == "sculpt":
            prefs.sculpt_lines.remove(self.index)
        else:  # modeling
            prefs.modeling_lines.remove(self.index)
            
        save_settings()
        
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return {'FINISHED'}

class MoveLineOperator(Operator):
    bl_idname = "viewport_notes.move_line"
    bl_label = "Move Line"
    bl_description = "Move this line up or down"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: bpy.props.IntProperty()
    mode: StringProperty(default="modeling")
    direction: StringProperty(default="up")
    
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        
        if self.mode == "sculpt":
            lines = prefs.sculpt_lines
        else:  # modeling
            lines = prefs.modeling_lines
        
        current_index = self.index
        if self.direction == "up":
            target_index = max(0, current_index - 1)
        else:  # down
            target_index = min(len(lines) - 1, current_index + 1)
        
        if current_index == target_index:
            return {'CANCELLED'}
        
        temp_text = lines[current_index].text
        lines[current_index].text = lines[target_index].text
        lines[target_index].text = temp_text
        
        save_settings()
        
        return {'FINISHED'}

class ToggleNotesPanelOperator(Operator):
    bl_idname = "viewport_notes.toggle_panel"
    bl_label = "Toggle Notes Panel"
    bl_description = "Expand or collapse the notes panel"
    bl_options = {'REGISTER'}
    
    mode: StringProperty(default="modeling")
    
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        
        if self.mode == "sculpt":
            prefs.sculpt_expanded = not prefs.sculpt_expanded
        else:  # modeling
            prefs.modeling_expanded = not prefs.modeling_expanded
            
        save_settings()
        return {'FINISHED'}

def update_hotkey(self, context):
    unregister_keymap()
    if self.use_hotkey:
        register_keymap()
    save_settings()

class ViewportNotesPreferences(AddonPreferences):
    bl_idname = __name__

    modeling_lines: CollectionProperty(
        type=NoteLine,
        name="Modeling Notes",
        description="Collection of text lines for Modeling mode"
    )
    
    sculpt_lines: CollectionProperty(
        type=NoteLine,
        name="Sculpt Notes",
        description="Collection of text lines for Sculpt mode"
    )
    
    use_mode_switching: BoolProperty(
        name="Switch Notes by Mode",
        description="Automatically switch between Modeling and Sculpt notes based on the current mode",
        default=True,
        update=lambda self, context: save_settings()
    )
    
    use_hotkey: BoolProperty(
        name="Enable Hotkey",
        description="Enable the hotkey for toggling notes visibility",
        default=True,
        update=lambda self, context: update_hotkey(self, context)
    )
    
    modeling_expanded: BoolProperty(
        name="Show Modeling Notes",
        description="Expand modeling notes section",
        default=True,
        update=lambda self, context: save_settings()
    )
    
    sculpt_expanded: BoolProperty(
        name="Show Sculpt Notes",
        description="Expand sculpt notes section",
        default=True,
        update=lambda self, context: save_settings()
    )
    
    opacity: FloatProperty(
        name="Прозрачность",
        description="Настройка прозрачности текста",
        default=0.7,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        update=lambda self, context: save_settings()
    )
    
    scale: FloatProperty(
        name="Масштаб",
        description="Настройка размера текста",
        default=0.7,
        min=0.5,
        max=2.0,
        subtype='FACTOR',
        update=lambda self, context: save_settings()
    )
    
    position: EnumProperty(
        name="Note's Position",
        description="Выберите позицию текста",
        items=position_items,
        default='BOTTOM_RIGHT',
        update=lambda self, context: save_settings()
    )
    
    scale_position: EnumProperty(
        name="Scale Position",
        description="Выберите позицию отображения масштаба",
        items=position_items,
        default='BOTTOM_LEFT',
        update=lambda self, context: save_settings()
    )

    show_scale: BoolProperty(
        name="Show Object Scale",
        description="Display scale of selected object in real-time",
        default=True,
        update=lambda self, context: save_settings()
    )
    
    hide_scale_on_hotkey: BoolProperty(
        name="Hide Scale on Hotkey",
        description="Hide scale information when toggling notes visibility with hotkey",
        default=False,
        update=lambda self, context: save_settings()
    )

    def draw(self, context):
        layout = self.layout
        
        # Hotkeys section
        box = layout.box()
        box.label(text="Горячие клавиши:")
        row = box.row()
        row.prop(self, "use_hotkey")
        row.prop(self, "hide_scale_on_hotkey")
        
        if self.use_hotkey:
            wm = context.window_manager
            kc = wm.keyconfigs.user
            if kc:
                km = kc.keymaps.get('3D View')
                if km:
                    for kmi in km.keymap_items:
                        if kmi.idname == "viewport_notes.toggle_visibility":
                            row = box.row()
                            col = row.column()
                            col.label(text="Toggle Notes Visibility")
                            col = row.column()
                            col.prop(kmi, "type", text="", full_event=True)
                            break
        
        layout.separator()
        
        # Mode switching and scale options
        layout.prop(self, "use_mode_switching")
        layout.prop(self, "show_scale")
        
        # Modeling Notes section with accordion
        box = layout.box()
        row = box.row()
        row.operator("viewport_notes.toggle_panel", text="", icon='TRIA_DOWN' if self.modeling_expanded else 'TRIA_RIGHT', emboss=False).mode = "modeling"
        row.label(text="Modeling Notes")
        
        if self.modeling_expanded:
            for i, line in enumerate(self.modeling_lines):
                row = box.row(align=True)
                row.label(text=f"{i + 1}.")
                row.prop(line, "text", text="")
                move_up = row.operator("viewport_notes.move_line", text="", icon='TRIA_UP')
                move_up.index = i
                move_up.mode = "modeling"
                move_up.direction = "up"
                move_down = row.operator("viewport_notes.move_line", text="", icon='TRIA_DOWN')
                move_down.index = i
                move_down.mode = "modeling"
                move_down.direction = "down"
                op = row.operator("viewport_notes.remove_line", text="", icon='X')
                op.index = i
                op.mode = "modeling"
            
            row = box.row()
            row.operator("viewport_notes.add_line", text="Добавить строку", icon='ADD').mode = "modeling"
        
        # Sculpt Notes section with accordion
        box = layout.box()
        row = box.row()
        row.operator("viewport_notes.toggle_panel", text="", icon='TRIA_DOWN' if self.sculpt_expanded else 'TRIA_RIGHT', emboss=False).mode = "sculpt"
        row.label(text="Sculpt Notes")
        
        if self.sculpt_expanded:
            for i, line in enumerate(self.sculpt_lines):
                row = box.row(align=True)
                row.label(text=f"{i + 1}.")
                row.prop(line, "text", text="")
                move_up = row.operator("viewport_notes.move_line", text="", icon='TRIA_UP')
                move_up.index = i
                move_up.mode = "sculpt"
                move_up.direction = "up"
                move_down = row.operator("viewport_notes.move_line", text="", icon='TRIA_DOWN')
                move_down.index = i
                move_down.mode = "sculpt" 
                move_down.direction = "down"
                op = row.operator("viewport_notes.remove_line", text="", icon='X')
                op.index = i
                op.mode = "sculpt"
            
            row = box.row()
            row.operator("viewport_notes.add_line", text="Добавить строку", icon='ADD').mode = "sculpt"
        
        layout.separator()
        
        layout.label(text="Внешний вид:")
        layout.prop(self, "opacity")
        layout.prop(self, "scale")
        layout.prop(self, "position")

        layout.separator()
        layout.label(text="Scale options:")
        layout.prop(self, "scale_position")

def get_position_coordinates(context, position):
    area_width = context.area.width
    area_height = context.area.height
    margin = 60
    
    positions = {
        'TOP_LEFT': (margin, area_height - margin),
        'TOP_RIGHT': (area_width - margin - 200, area_height - margin),
        'BOTTOM_LEFT': (margin, margin),
        'BOTTOM_RIGHT': (area_width - margin - 200, margin),
    }
    
    return positions.get(position)

def draw_outlined_text(font_id, text, x, y, size, opacity, outline_width=1):
    blf.size(font_id, size)
    blf.color(font_id, 0, 0, 0, opacity)
    offsets = [
        (-outline_width, -outline_width), (0, -outline_width), (outline_width, -outline_width),
        (-outline_width, 0),                                   (outline_width, 0),
        (-outline_width, outline_width),  (0, outline_width),  (outline_width, outline_width)
    ]
    
    for offset_x, offset_y in offsets:
        blf.position(font_id, x + offset_x, y + offset_y, 0)
        blf.draw(font_id, text)
    
    blf.color(font_id, 1, 1, 1, opacity)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, text)

def draw_notes_info():
    area = bpy.context.area
    if not viewport_notes_show_per_area.get(area, True):
        return
        
    prefs = bpy.context.preferences.addons[__name__].preferences
    
    current_mode = bpy.context.mode
    
    if prefs.use_mode_switching and current_mode == 'SCULPT':
        notes = [line.text.strip() for line in prefs.sculpt_lines if line.text.strip()]
    else:
        notes = [line.text.strip() for line in prefs.modeling_lines if line.text.strip()]
    
    if not notes:
        return
    
    x, base_y = get_position_coordinates(bpy.context, prefs.position)
    
    font_id = 0
    font_size = int(16 * prefs.scale)
    line_height = int(21 * prefs.scale)
    
    for i, text in enumerate(notes):
        y = base_y - (i * line_height) if prefs.position in ['TOP_LEFT', 'TOP_RIGHT'] else base_y + ((len(notes) - 1 - i) * line_height)
        draw_outlined_text(font_id, text, x, y, font_size, prefs.opacity, outline_width=1)
        
def draw_scale_info(context):
    prefs = context.preferences.addons[__name__].preferences
    area = context.area
    
    # Не показывать масштаб если кнопка отключена через горячую клавишу
    if prefs.hide_scale_on_hotkey and not viewport_notes_show_per_area.get(area, True):
        return

    # Не показывать масштаб, если отключена опция
    if not prefs.show_scale:
        return
        
    # Добавляем проверку на режим Sculpt и не показываем Scale в этом режиме
    current_mode = context.mode
    if current_mode == 'SCULPT':
        return

    obj = context.active_object
    if not obj or obj.type != 'MESH' or not context.selected_objects:
        return

    scale_x = round(obj.scale.x, 3)
    scale_y = round(obj.scale.y, 3)
    scale_z = round(obj.scale.z, 3)

    font_id = 0
    font_size = int(16 * prefs.scale)
    opacity = prefs.opacity
    line_height = int(21 * prefs.scale)

    x, base_y = get_position_coordinates(context, prefs.scale_position)

    texts = [
        "Scale:",
        f"X: {scale_x}",
        f"Y: {scale_y}",
        f"Z: {scale_z}"
    ]

    for i, text in enumerate(texts):
        y = base_y - (i * line_height) if prefs.scale_position in ['TOP_LEFT', 'TOP_RIGHT'] else base_y + ((len(texts) - 1 - i) * line_height)
        draw_outlined_text(font_id, text, x, y, font_size, opacity)

def draw_callback_px():
    draw_notes_info()
    if bpy.context.active_object:
        draw_scale_info(bpy.context)

class VIEW3D_PT_viewport_notes(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_parent_id = 'VIEW3D_PT_overlay'
    bl_label = "Guides"
    
    def draw(self, context):
        layout = self.layout
        layout.prop(context.window_manager, "viewport_notes_show", text="Custom Notes")
        
        if context.window_manager.viewport_notes_show:
            prefs = context.preferences.addons[__name__].preferences
            if prefs.use_mode_switching:
                current_mode = context.mode
                if current_mode == 'SCULPT':
                    layout.label(text="Showing: Sculpt Notes")
                else:
                    layout.label(text="Showing: Modeling Notes")

class ToggleNotesVisibilityOperator(Operator):
    bl_idname = "viewport_notes.toggle_visibility"
    bl_label = "Toggle Notes Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def execute(self, context):
        area = context.area
        current_state = viewport_notes_show_per_area.get(area, True)
        viewport_notes_show_per_area[area] = not current_state
        context.area.tag_redraw()
        return {'FINISHED'}

addon_keymaps = []

def register_keymap():
    unregister_keymap()
    prefs = bpy.context.preferences.addons.get(__name__)
    if prefs and not prefs.preferences.use_hotkey:
        return
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            idname="viewport_notes.toggle_visibility",
            type='Q',
            value='PRESS',
            ctrl=True
        )
        addon_keymaps.append((km, kmi))
        if wm.keyconfigs.user:
            km_user = wm.keyconfigs.user.keymaps.get('3D View')
            if km_user:
                kmi_user = km_user.keymap_items.new(
                    idname="viewport_notes.toggle_visibility",
                    type=kmi.type,
                    value=kmi.value,
                    ctrl=kmi.ctrl,
                    shift=kmi.shift,
                    alt=kmi.alt
                )

def unregister_keymap():
    for km, kmi in addon_keymaps:
        if kmi:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    wm = bpy.context.window_manager
    if wm.keyconfigs.user:
        km = wm.keyconfigs.user.keymaps.get('3D View')
        if km:
            for kmi in km.keymap_items:
                if kmi.idname == "viewport_notes.toggle_visibility":
                    km.keymap_items.remove(kmi)

def check_mode_change(scene):
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except:
        pass

classes = [
    NoteLine,
    AddLineOperator,
    RemoveLineOperator,
    MoveLineOperator,
    ToggleNotesPanelOperator,
    ViewportNotesPreferences,
    VIEW3D_PT_viewport_notes,
    ToggleNotesVisibilityOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.WindowManager.viewport_notes_show = bpy.props.BoolProperty(
        default=True,
        update=lambda self, context: save_settings()
    )
    
    bpy.app.handlers.depsgraph_update_post.append(check_mode_change)
    
    settings = load_settings()
    if settings:
        try:
            prefs = bpy.context.preferences.addons[__name__].preferences
            prefs.modeling_lines.clear()
            for text in settings.get('modeling_lines', settings.get('lines', [])):
                line = prefs.modeling_lines.add()
                line.text = text
            prefs.sculpt_lines.clear()
            for text in settings.get('sculpt_lines', []):
                line = prefs.sculpt_lines.add()
                line.text = text
            prefs.opacity = settings.get('opacity', 0.7)
            prefs.scale = settings.get('scale', 0.7)
            prefs.position = settings.get('position', 'BOTTOM_RIGHT')
            prefs.show_scale = settings.get('show_scale', True)
            prefs.use_mode_switching = settings.get('use_mode_switching', True)
            prefs.modeling_expanded = settings.get('modeling_expanded', True)
            prefs.sculpt_expanded = settings.get('sculpt_expanded', True)
            prefs.use_hotkey = settings.get('use_hotkey', True)
            prefs.hide_scale_on_hotkey = settings.get('hide_scale_on_hotkey', False)
            bpy.context.window_manager.viewport_notes_show = settings.get('show_notes', True)
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    if bpy.context.preferences.addons[__name__].preferences.use_hotkey:
        register_keymap()
    bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')

def unregister():
    if check_mode_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(check_mode_change)
    save_settings()
    unregister_keymap()
    del bpy.types.WindowManager.viewport_notes_show
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

if __name__ == "__main__":
    register()