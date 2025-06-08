bl_info = {
    "name": "Auto XRay for Wireframe with State Restore",
    "author": "eRisonv",
    "version": (1, 3),
    "blender": (4, 0, 2),
    "location": "View3D",
    "description": "Включает XRay в режиме wireframe и восстанавливает прежнее состояние при выходе",
    "category": "3D View",
}

import bpy
from bpy.app.handlers import persistent

# Ваши глобальные переменные
_running = False
_xray_states = {}

@persistent
def load_post_handler(dummy):
    global _xray_states
    _xray_states.clear()
    # Если нужно, можно также перерегистрировать таймер:
    bpy.app.timers.register(auto_xray_timer)

def auto_xray_timer():
    global _running, _xray_states
    if not _running:
        return None
    # Здесь код проверки пространств и управления show_xray_wireframe
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        shading = space.shading
                        key = id(space)
                        if shading.type == 'WIREFRAME':
                            if key not in _xray_states:
                                _xray_states[key] = shading.show_xray_wireframe
                            if not shading.show_xray_wireframe:
                                shading.show_xray_wireframe = True
                        else:
                            if key in _xray_states:
                                shading.show_xray_wireframe = _xray_states[key]
                                del _xray_states[key]
    return 0.5

def register():
    global _running
    _running = True
    bpy.app.timers.register(auto_xray_timer)
    # Регистрируем обработчик загрузки
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)

def unregister():
    global _running, _xray_states
    _running = False
    _xray_states.clear()
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

if __name__ == "__main__":
    register()
