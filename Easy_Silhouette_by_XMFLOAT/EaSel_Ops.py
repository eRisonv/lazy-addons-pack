import bpy
from bpy.app.handlers import persistent

def get_shading_info():
    try:
        # Получаем текущий тип фона
        x0 = bpy.context.space_data.shading.background_type

        # Цвет фона в RGB
        x1_r = bpy.context.space_data.shading.background_color[0]
        x1_g = bpy.context.space_data.shading.background_color[1]
        x1_b = bpy.context.space_data.shading.background_color[2]
        x1 = x1_r, x1_g, x1_b
   
        # Текущий тип отображения
        x2 = bpy.context.space_data.shading.type

        # Тип освещения
        x3 = bpy.context.space_data.shading.light
   
        # Тип цвета
        x4 = bpy.context.space_data.shading.color_type

        # Единый цвет в RGB
        x5_r = bpy.context.space_data.shading.single_color[0]
        x5_g = bpy.context.space_data.shading.single_color[1]
        x5_b = bpy.context.space_data.shading.single_color[2]
        x5 = x5_r, x5_g, x5_b

        # Состояние наложения
        x6 = bpy.context.space_data.overlay.show_overlays

        # Состояние теней и впадин
        x7 = bpy.context.space_data.shading.show_shadows
        x8 = bpy.context.space_data.shading.show_cavity
   
        return (x0, x1, x2, x3, x4, x5, x6, x7, x8)
    except Exception as e:
        print(f"Ошибка получения информации о затенении: {e}")
        # Возвращаем безопасные дефолтные настройки
        return (
            'VIEWPORT', # background_type
            (1, 1, 1), # background_color
            'SOLID', # shading type
            'FLAT', # light
            'SINGLE', # color_type
            (0, 0, 0), # single_color
            True, # show_overlays
            False, # show_shadows
            False # show_cavity
        )

def get_valid_3d_space():
    """Получает валидный 3D viewport space_data"""
    # Сначала пробуем текущий контекст
    if hasattr(bpy.context, 'space_data') and bpy.context.space_data and bpy.context.space_data.type == 'VIEW_3D':
        return bpy.context.space_data
    
    # Ищем в открытых окнах
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        return space
    
    return None
        
# Глобальная переменная для хранения предыдущих настроек
precede_info = 0

class EaSel_Silhouette_On(bpy.types.Operator):
    """Enable silhouette mode"""
    bl_idname = "easel.silhouette_on"
    bl_label = "Enable Silhouette"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            easel_props = context.scene.easel_prop
            space_data = get_valid_3d_space()
            
            if not space_data:
                self.report({'ERROR'}, "Не найден активный 3D viewport")
                return {'CANCELLED'}
                
            shading = space_data.shading
            overlay = space_data.overlay

            # Логирование перед сохранением
            print("\n=== Saving Silhouette Settings ===")
            print(f"Original Shading Type: {shading.type}")
            print(f"Original Background: {shading.background_type}")
            print(f"Original Overlays: {overlay.show_overlays}")

            # Сохраняем текущие настройки
            easel_props.prev_background_type = shading.background_type
            easel_props.prev_background_color = shading.background_color[:]
            easel_props.prev_shading_type = shading.type
            easel_props.prev_light = shading.light
            easel_props.prev_color_type = shading.color_type
            easel_props.prev_single_color = shading.single_color[:]
            easel_props.prev_show_overlays = overlay.show_overlays
            easel_props.prev_show_shadows = shading.show_shadows
            easel_props.prev_show_cavity = shading.show_cavity
            easel_props.prev_settings_saved = True

            # Логирование после сохранения
            print("=== Saved Settings ===")
            print(f"Saved Shading Type: {easel_props.prev_shading_type}")
            print(f"Saved Overlays State: {easel_props.prev_show_overlays}")

            # Устанавливаем новые настройки
            addon_prefs = context.preferences.addons[__package__].preferences
            shading.background_type = 'VIEWPORT'
            shading.background_color = addon_prefs.background_color
            shading.type = 'SOLID'
            shading.light = 'FLAT'
            shading.color_type = 'SINGLE'
            shading.single_color = addon_prefs.mesh_color
            overlay.show_overlays = False
            shading.show_shadows = False
            shading.show_cavity = False

            print("=== Silhouette Activated ===")
            return {'FINISHED'}
            
        except Exception as e:
            print(f"Ошибка включения силуэта: {e}")
            self.report({'ERROR'}, f"Ошибка включения силуэта: {str(e)}")
            return {'CANCELLED'}

class EaSel_Silhouette_Off(bpy.types.Operator):
    """Disable silhouette mode"""
    bl_idname = "easel.silhouette_off"
    bl_label = "Disable Silhouette"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            easel_props = context.scene.easel_prop
            space_data = get_valid_3d_space()

            if not space_data:
                print("!!! Error: Не найден валидный 3D viewport")
                self.report({'ERROR'}, "Не найден активный 3D viewport")
                return {'CANCELLED'}

            shading = space_data.shading
            overlay = space_data.overlay

            print("\n=== Attempting to Restore Settings ===")
            print(f"Settings Saved Flag: {easel_props.prev_settings_saved}")

            has_prev_settings = easel_props.prev_settings_saved

            if has_prev_settings:
                print("=== Restoring Saved Settings ===")
                print(f"Restoring Shading Type: {easel_props.prev_shading_type}")
                print(f"Restoring Overlays: {easel_props.prev_show_overlays}")

                # Восстанавливаем настройки по одной с проверкой
                try:
                    shading.background_type = easel_props.prev_background_type
                    shading.background_color = easel_props.prev_background_color
                    shading.type = easel_props.prev_shading_type
                    shading.light = easel_props.prev_light
                    shading.color_type = easel_props.prev_color_type
                    shading.single_color = easel_props.prev_single_color
                    overlay.show_overlays = easel_props.prev_show_overlays
                    shading.show_shadows = easel_props.prev_show_shadows
                    shading.show_cavity = easel_props.prev_show_cavity

                    # Сбрасываем флаг только после успешного восстановления
                    easel_props.prev_settings_saved = False
                    print("Settings restored successfully")
                    
                except Exception as restore_error:
                    print(f"Ошибка восстановления настроек: {restore_error}")
                    # Пытаемся восстановить хотя бы базовые настройки
                    self.restore_default_settings(shading, overlay)
                    easel_props.prev_settings_saved = False
                    
            else:
                print("=== No Saved Settings - Checking Current State ===")
                print("Current State Check:")
                print(f"Shading Type: {shading.type}")
                print(f"Background Type: {shading.background_type}")
                print(f"Overlays: {overlay.show_overlays}")
                
                addon_prefs = context.preferences.addons[__package__].preferences
                is_silhouette = self.is_silhouette_active(shading, overlay, addon_prefs)
                
                print(f"Is Silhouette Active: {is_silhouette}")
                
                if is_silhouette:
                    print("Restoring Default Settings")
                    self.restore_default_settings(shading, overlay)
                else:
                    print("No restoration needed")

            # Принудительно обновляем viewport
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            return {'FINISHED'}
            
        except Exception as e:
            print(f"Критическая ошибка выключения силуэта: {e}")
            self.report({'ERROR'}, f"Ошибка выключения силуэта: {str(e)}")
            return {'CANCELLED'}

    def is_silhouette_active(self, shading, overlay, addon_prefs):
        """Проверяет, активен ли режим силуэта"""
        try:
            return (
                shading.background_type == 'VIEWPORT' and
                all(abs(c - addon_prefs.background_color[i]) < 0.001 for i, c in enumerate(shading.background_color)) and
                shading.type == 'SOLID' and
                shading.light == 'FLAT' and
                shading.color_type == 'SINGLE' and
                all(abs(c - addon_prefs.mesh_color[i]) < 0.001 for i, c in enumerate(shading.single_color)) and
                not overlay.show_overlays and
                not shading.show_shadows and
                not shading.show_cavity
            )
        except Exception:
            return False

    def restore_default_settings(self, shading, overlay):
        """Восстанавливает настройки по умолчанию"""
        try:
            shading.background_type = 'THEME'
            shading.type = 'SOLID'
            shading.light = 'STUDIO'
            shading.color_type = 'MATERIAL'
            shading.single_color = (0.8, 0.8, 0.8)
            overlay.show_overlays = True
            shading.show_shadows = True
            shading.show_cavity = True
        except Exception as e:
            print(f"Ошибка восстановления дефолтных настроек: {e}")

class EaSel_Toggle_Silhouette(bpy.types.Operator):
    """Toggle silhouette mode"""
    bl_idname = "easel.toggle_silhouette"
    bl_label = "Toggle Silhouette"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            easel_tool = context.scene.easel_prop
            new_state = not easel_tool.easel_button
            print(f"\n=== Toggling Silhouette: {new_state} ===")
            print(f"Previous State: {easel_tool.easel_button}")
            easel_tool.easel_button = new_state
            return {'FINISHED'}
        except Exception as e:
            print(f"!!! Toggle Error: {str(e)}")
            self.report({'ERROR'}, f"Ошибка переключения: {str(e)}")
            return {'CANCELLED'}

class EaSel_Force_Reset(bpy.types.Operator):
    """Force reset silhouette mode - emergency button"""
    bl_idname = "easel.force_reset"
    bl_label = "Force Reset Silhouette"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            print("\n=== FORCE RESET ACTIVATED ===")
            easel_props = context.scene.easel_prop
            space_data = get_valid_3d_space()
            
            if not space_data:
                # Если не можем найти 3D viewport, пробуем все области
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        space_data = area.spaces[0]
                        break
            
            if not space_data:
                self.report({'ERROR'}, "Не найден 3D viewport для сброса")
                return {'CANCELLED'}
            
            shading = space_data.shading
            overlay = space_data.overlay
            
            # Принудительно сбрасываем все настройки к дефолтным
            print("Forcing default viewport settings...")
            shading.background_type = 'THEME'
            shading.type = 'SOLID'  
            shading.light = 'STUDIO'
            shading.color_type = 'MATERIAL'
            shading.single_color = (0.8, 0.8, 0.8)
            overlay.show_overlays = True
            shading.show_shadows = True  
            shading.show_cavity = True
            
            # Сбрасываем состояние аддона
            easel_props.easel_button = False
            easel_props.prev_settings_saved = False
            
            # Принудительно обновляем все 3D viewports
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            print("Force reset completed")
            self.report({'INFO'}, "Силуэт принудительно сброшен")
            return {'FINISHED'}
            
        except Exception as e:
            print(f"Ошибка принудительного сброса: {e}")
            self.report({'ERROR'}, f"Ошибка сброса: {str(e)}")
            return {'CANCELLED'}

class EaSel_Smart_Toggle(bpy.types.Operator):
    """Smart toggle - normal click toggles, Shift+click force resets"""
    bl_idname = "easel.smart_toggle"
    bl_label = "Toggle Silhouette (Shift+Click to Force Reset)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        # Проверяем, зажат ли Shift
        if event.shift:
            print("\n=== SHIFT+CLICK DETECTED - FORCE RESET ===")
            return bpy.ops.easel.force_reset('INVOKE_DEFAULT')
        else:
            print("\n=== NORMAL CLICK - TOGGLE ===")
            return bpy.ops.easel.toggle_silhouette('INVOKE_DEFAULT')

classes = (
    EaSel_Silhouette_On,
    EaSel_Silhouette_Off,
    EaSel_Toggle_Silhouette,
    EaSel_Force_Reset,
    EaSel_Smart_Toggle,
)

@persistent
def load_post_handler(dummy):
    """Обработчик загрузки файла - проверяет состояние силуэта"""
    try:
        # Проверяем все сцены
        for scene in bpy.data.scenes:
            if not hasattr(scene, 'easel_prop'):
                continue
                
            easel_props = scene.easel_prop
            
            # Получаем валидный 3D viewport
            space_data = get_valid_3d_space()
            if not space_data:
                continue
                
            # Получаем настройки аддона
            try:
                addon_prefs = bpy.context.preferences.addons[__package__].preferences
            except:
                # Если аддон еще не загружен полностью, пропускаем
                continue
            
            shading = space_data.shading
            overlay = space_data.overlay
            
            # Проверяем, активен ли силуэт визуально
            is_silhouette_visual = (
                shading.background_type == 'VIEWPORT' and
                shading.type == 'SOLID' and
                shading.light == 'FLAT' and
                shading.color_type == 'SINGLE' and
                not overlay.show_overlays and
                not shading.show_shadows and
                not shading.show_cavity
            )
            
            print(f"\n=== Load Post Handler ===")
            print(f"Scene: {scene.name}")
            print(f"Button State: {easel_props.easel_button}")
            print(f"Visual Silhouette: {is_silhouette_visual}")
            print(f"Settings Saved Flag: {easel_props.prev_settings_saved}")
            
            # Синхронизируем состояние
            if is_silhouette_visual and not easel_props.easel_button:
                print("Fixing: Visual silhouette ON, but button OFF")
                easel_props.easel_button = True
                # Устанавливаем флаг, что настройки НЕ сохранены (т.к. мы загрузились с силуэтом)
                easel_props.prev_settings_saved = False
                
            elif not is_silhouette_visual and easel_props.easel_button:
                print("Fixing: Visual silhouette OFF, but button ON")
                easel_props.easel_button = False
                easel_props.prev_settings_saved = False
                
    except Exception as e:
        print(f"Ошибка в load_post_handler: {e}")

def register():
    # Регистрируем классы
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)
    
    # Регистрируем обработчик загрузки файлов
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)

def unregister():
    # Удаляем обработчик загрузки файлов
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    
    # Удаляем классы
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass

if __name__ == "__main__":
    register()