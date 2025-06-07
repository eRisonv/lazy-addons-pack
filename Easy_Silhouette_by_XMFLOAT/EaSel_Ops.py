import bpy

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
        
# Глобальная переменная для хранения предыдущих настроек
precede_info = 0

class EaSel_Silhouette_On(bpy.types.Operator):
    """Enable silhouette mode"""
    bl_idname = "easel.silhouette_on"
    bl_label = "Enable Silhouette"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        easel_props = context.scene.easel_prop
        space_data = context.space_data
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
        easel_props.prev_settings_saved = True  # Новая флаговая переменная

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

class EaSel_Silhouette_Off(bpy.types.Operator):
    """Disable silhouette mode"""
    bl_idname = "easel.silhouette_off"
    bl_label = "Disable Silhouette"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        easel_props = context.scene.easel_prop
        space_data = context.space_data

        if not space_data or space_data.type != 'VIEW_3D':
            print("!!! Error: Invalid space data")
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

            shading.background_type = easel_props.prev_background_type
            shading.background_color = easel_props.prev_background_color
            shading.type = easel_props.prev_shading_type
            shading.light = easel_props.prev_light
            shading.color_type = easel_props.prev_color_type
            shading.single_color = easel_props.prev_single_color
            overlay.show_overlays = easel_props.prev_show_overlays
            shading.show_shadows = easel_props.prev_show_shadows
            shading.show_cavity = easel_props.prev_show_cavity

            # Сбрасываем флаг
            easel_props.prev_settings_saved = False
            print("Settings flag reset")
        else:
            print("=== No Saved Settings ===")
            print("Current State Check:")
            print(f"Shading Type: {shading.type}")
            print(f"Background Type: {shading.background_type}")
            print(f"Overlays: {overlay.show_overlays}")
            
            addon_prefs = context.preferences.addons[__package__].preferences
            is_silhouette = (
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
            
            print(f"Is Silhouette Active: {is_silhouette}")
            
            if is_silhouette:
                print("Restoring Default Settings")
                shading.background_type = 'THEME'
                shading.type = 'SOLID'
                shading.light = 'STUDIO'
                shading.color_type = 'MATERIAL'
                shading.single_color = (0.8, 0.8, 0.8)
                overlay.show_overlays = True
                shading.show_shadows = True
                shading.show_cavity = True
            else:
                print("No restoration needed")

        return {'FINISHED'}

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
            return {'CANCELLED'}

classes = (
    EaSel_Silhouette_On,
    EaSel_Silhouette_Off,
    EaSel_Toggle_Silhouette,
)

def register():
    # Регистрируем классы
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)

def unregister():
    # Удаляем классы
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass

if __name__ == "__main__":
    register()