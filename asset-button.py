import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty
from bpy.types import AddonPreferences, GizmoGroup, Operator, Scene, PropertyGroup
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Sticky Asset Browser",
    "author": "Asset Browser Expert",
    "description": "Quickly toggle Asset Browser in 3D Viewport area",
    "blender": (4, 0, 0),
    "version": (1, 0, 0),
    "location": "3D Viewport",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Asset"
}


class AssetBrowserSettings(PropertyGroup):
    """Settings for Asset Browser configuration"""
    app_version = bpy.app.version
    initialized: BoolProperty(default=False)
    
    show_region_toolbar: BoolProperty(
        name="Show Toolbar",
        description="Show Asset Browser toolbar",
        default=True)
    show_region_ui: BoolProperty(
        name="Show Sidebar",
        description="Show Asset Browser sidebar",
        default=True)
    show_region_header: BoolProperty(
        name="Show Header",
        description="Show Asset Browser header",
        default=True)
    
    def set(self, area):
        """Apply settings to Asset Browser area"""
        try:
            space = area.spaces[0]
            # Only set attributes that exist for SpaceFileBrowser
            if hasattr(space, 'show_region_toolbar'):
                space.show_region_toolbar = self.show_region_toolbar
            if hasattr(space, 'show_region_ui'):
                space.show_region_ui = self.show_region_ui
            if hasattr(space, 'show_region_header'):
                space.show_region_header = self.show_region_header
        except Exception as e:
            print(f"Error in AssetBrowserSettings.set: {e}")
    
    def save_from_area(self, area):
        """Save settings from Asset Browser area"""
        try:
            space = area.spaces[0]
            # Only save attributes that exist for SpaceFileBrowser
            if hasattr(space, 'show_region_toolbar'):
                self.show_region_toolbar = space.show_region_toolbar
            if hasattr(space, 'show_region_ui'):
                self.show_region_ui = space.show_region_ui
            if hasattr(space, 'show_region_header'):
                self.show_region_header = space.show_region_header
        except Exception as e:
            print(f"Error in AssetBrowserSettings.save_from_area: {e}")
    
    def save_from_property(self, property):
        """Save settings from property group"""
        try:
            self.show_region_toolbar = property.show_region_toolbar
            self.show_region_ui = property.show_region_ui
            self.show_region_header = property.show_region_header
        except Exception as e:
            print(f"Error in AssetBrowserSettings.save_from_property: {e}")


class StickyAssetBrowserPreferences(AddonPreferences):
    bl_idname = __name__

    settings_tabs: EnumProperty(
        items=[
            ("GENERAL", "General", "General settings"),
            ("VIEW", "View", "View settings")
        ],
        default="GENERAL"
    )

    asset_browser_side: EnumProperty(
        name="Asset Browser Side",
        description="3D Viewport area side where to open Asset Browser",
        items=[
            ('LEFT', "Left", "Open Asset Browser on the left side of 3D Viewport area"),
            ('RIGHT', "Right", "Open Asset Browser on the right side of 3D Viewport area"),
            ('BOTTOM', "UP", "Open Asset Browser on the bottom of 3D Viewport area")
        ],
        default='RIGHT'
    )
    
    show_ui_button: BoolProperty(
        name="Show Overlay Button",
        description="Show overlay button on corresponding side of 3D Viewport",
        default=True
    )
    
    remember_asset_browser_settings: BoolProperty(
        name="Remember Asset Browser Settings",
        description="Remember changes made in Asset Browser area",
        default=True
    )
    
    asset_browser_settings: PointerProperty(type=AssetBrowserSettings)
    
    split_factor: EnumProperty(
        name="Split Factor",
        description="How much space Asset Browser should take",
        items=[
            ('0.3', "30%", "Asset Browser takes 30% of space"),
            ('0.4', "40%", "Asset Browser takes 40% of space"),
            ('0.5', "50%", "Asset Browser takes 50% of space"),
            ('0.6', "60%", "Asset Browser takes 60% of space")
        ],
        default='0.3'
    )

    def draw(self, context):
        layout = self.layout
        layout.row().prop(self, "settings_tabs", expand=True)

        if self.settings_tabs == 'GENERAL':
            box = layout.box()
            col = box.column()
            col.label(text="Add-on Settings:")
            col.separator()
            col.prop(self, "asset_browser_side")
            col.prop(self, "split_factor")
            col.prop(self, "show_ui_button")
            col.prop(self, "remember_asset_browser_settings")

        elif self.settings_tabs == 'VIEW':
            box = layout.box()
            col = box.column()
            col.label(text="Asset Browser View Settings:")
            col.separator()
            col.prop(self.asset_browser_settings, "show_region_toolbar")
            col.prop(self.asset_browser_settings, "show_region_ui")
            col.prop(self.asset_browser_settings, "show_region_header")


def safe_area_close(context, area_to_close):
    """Safely close an area using proper context override"""
    try:
        app_version = bpy.app.version
        
        if app_version >= (3, 2, 0):
            # Modern Blender versions - use context.temp_override()
            with context.temp_override(area=area_to_close):
                bpy.ops.screen.area_close()
        elif app_version >= (3, 0, 0):
            # Blender 3.0-3.1 - use dictionary context
            try:
                bpy.ops.screen.area_close({'area': area_to_close})
            except ValueError as e:
                print(f"Error in safe_area_close (Blender 3.0-3.1): {e}")
                # Fallback to area join
                area_x = area_to_close.x + 10
                area_y = area_to_close.y + 10
                bpy.ops.screen.area_join(cursor=(area_x, area_y))
        else:
            # Older versions - use area join
            area_x = area_to_close.x + 10
            area_y = area_to_close.y + 10
            bpy.ops.screen.area_join(cursor=(area_x, area_y))
    except Exception as e:
        print(f"Error in safe_area_close: {e}")


class StickyAssetBrowser(Operator):
    """Show/Hide Asset Browser on the specified side of the 3D Viewport.
Hold 'Alt' to open Asset Browser in a separate window."""
    bl_idname = "wm.sticky_asset_browser"
    bl_label = "Sticky Asset Browser"
    bl_options = {'INTERNAL'}

    ui_button: BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        try:
            return context.area.ui_type in ['ASSETS', 'VIEW_3D']
        except Exception as e:
            return False

    def invoke(self, context, event):
        try:
            scene = context.scene
            active_area = context.area
            app_version = bpy.app.version


            if not event.alt:
                if context.window.screen.show_fullscreen:
                    self.report({'WARNING'}, "Sticky Asset Browser: Fullscreen mode is not supported!")
                    return {'FINISHED'}

                areas = context.screen.areas
                active_area_x = active_area.x
                active_area_y = active_area.y
                active_area_width = active_area.width
                active_area_height = active_area.height

                # Close existing Asset Browser
                if active_area.ui_type == 'ASSETS':
                    for area in areas:
                        if area.ui_type == 'VIEW_3D':
                            area_x = area.x
                            area_y = area.y
                            area_width = area.width
                            area_height = area.height

                            # Check if areas are adjacent
                            is_adjacent = False
                            
                            # Horizontal adjacency
                            if abs(area_y - active_area_y) < 20 and abs(area_height - active_area_height) < 20:
                                if abs((area_x + area_width) - active_area_x) < 20 or abs((active_area_x + active_area_width) - area_x) < 20:
                                    is_adjacent = True
                            
                            # Vertical adjacency
                            if abs(area_x - active_area_x) < 20 and abs(area_width - active_area_width) < 20:
                                if abs((area_y + area_height) - active_area_y) < 20 or abs((active_area_y + active_area_height) - area_y) < 20:
                                    is_adjacent = True

                            if is_adjacent:
                                # Save Asset Browser area settings
                                if hasattr(scene, 'asset_browser_settings'):
                                    scene.asset_browser_settings.save_from_area(active_area)

                                # Close Asset Browser area using safe method
                                safe_area_close(context, active_area)
                                return {'FINISHED'}

                    self.report({'WARNING'}, "Sticky Asset Browser: Failed to figure out current layout!")
                    return {'FINISHED'}

                elif active_area.ui_type == 'VIEW_3D':
                    # Check if Asset Browser already exists
                    for area in areas:
                        if area.ui_type == 'ASSETS':
                            area_x = area.x
                            area_y = area.y
                            area_width = area.width
                            area_height = area.height

                            # Check if areas are adjacent
                            is_adjacent = False
                            
                            # Horizontal adjacency
                            if abs(area_y - active_area_y) < 20 and abs(area_height - active_area_height) < 20:
                                if abs((area_x + area_width) - active_area_x) < 20 or abs((active_area_x + active_area_width) - area_x) < 20:
                                    is_adjacent = True
                            
                            # Vertical adjacency
                            if abs(area_x - active_area_x) < 20 and abs(area_width - active_area_width) < 20:
                                if abs((area_y + area_height) - active_area_y) < 20 or abs((active_area_y + active_area_height) - area_y) < 20:
                                    is_adjacent = True

                            if is_adjacent:
                                # Save Asset Browser area settings
                                if hasattr(scene, 'asset_browser_settings'):
                                    scene.asset_browser_settings.save_from_area(area)

                                # Close Asset Browser area using safe method
                                safe_area_close(context, area)
                                return {'FINISHED'}

                # Split active 3D View area
                addon_prefs = context.preferences.addons[__name__].preferences
                split_factor = float(addon_prefs.split_factor)
                
                if addon_prefs.asset_browser_side == 'BOTTOM':
                    bpy.ops.screen.area_split(direction='HORIZONTAL', factor=1.0 - split_factor)
                else:
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=split_factor)

            # Open Asset Browser
            addon_prefs = context.preferences.addons[__name__].preferences

            if addon_prefs.asset_browser_side == 'LEFT':
                for area in reversed(context.screen.areas):
                    if area.ui_type == 'VIEW_3D':
                        asset_area = area
                        break
            elif addon_prefs.asset_browser_side == 'BOTTOM':
                # Find the bottom area after split
                for area in context.screen.areas:
                    if area.ui_type == 'VIEW_3D' and area.y < active_area.y:
                        asset_area = area
                        break
            else:  # RIGHT
                asset_area = active_area

            ui_type = active_area.ui_type
            asset_area.ui_type = 'ASSETS'

            # Set Asset Browser area settings
            if hasattr(scene, 'asset_browser_settings'):
                asset_browser_settings = scene.asset_browser_settings

                if (not asset_browser_settings.initialized) or (not addon_prefs.remember_asset_browser_settings):
                    asset_browser_settings.save_from_property(addon_prefs.asset_browser_settings)
                    asset_browser_settings.initialized = True

                asset_browser_settings.set(asset_area)

            # Open Asset Browser in new window
            if event.alt:
                print("Duplicating area for new window")
                bpy.ops.screen.area_dupli('INVOKE_DEFAULT')
                active_area.ui_type = ui_type

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Sticky Asset Browser: Error during execution - {e}")
            print(f"Error in StickyAssetBrowser.invoke: {e}")
            return {'CANCELLED'}


class StickyAssetBrowser_UI_Button(GizmoGroup):
    bl_idname = "StickyAssetBrowser_UI_Button"
    bl_label = "Sticky Asset Browser UI Button"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        try:
            addon_prefs = context.preferences.addons[__name__].preferences
            return (addon_prefs.show_ui_button) and (not context.window.screen.show_fullscreen)
        except Exception as e:
            print(f"Error in StickyAssetBrowser_UI_Button.poll: {e}")
            return False

    def draw_prepare(self, context):
        try:
            addon_prefs = context.preferences.addons[__name__].preferences
            ui_scale = context.preferences.view.ui_scale

            width = 0
            padding = 20 * ui_scale

            if addon_prefs.asset_browser_side == 'LEFT':
                for region in context.area.regions:
                    if region.type == "TOOLS":
                        width = region.width
                        break
                self.asset_gizmo.matrix_basis[0][3] = width + padding
                self.asset_gizmo.matrix_basis[1][3] = context.region.height * 0.6

            elif addon_prefs.asset_browser_side == 'RIGHT':
                for region in context.area.regions:
                    if region.type == "UI":
                        width = region.width
                        break
                self.asset_gizmo.matrix_basis[0][3] = context.region.width - padding - width
                self.asset_gizmo.matrix_basis[1][3] = context.region.height * 0.6

            else:  # BOTTOM
                self.asset_gizmo.matrix_basis[0][3] = context.region.width * 0.9
                self.asset_gizmo.matrix_basis[1][3] = padding * 3
        except Exception as e:
            print(f"Error in StickyAssetBrowser_UI_Button.draw_prepare: {e}")

    def setup(self, context):
        try:
            mpr = self.gizmos.new("GIZMO_GT_button_2d")
            mpr.show_drag = False
            mpr.icon = 'ASSET_MANAGER'
            mpr.draw_options = {'BACKDROP', 'OUTLINE'}

            # Default color (neutral, e.g., gray)
            mpr.color = 0.0, 0.0, 0.0
            mpr.alpha = 0.6
            # Hover color (blue)
            mpr.color_highlight = 0.2, 0.5, 0.8
            mpr.alpha_highlight = 0.8

            mpr.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C
            op = mpr.target_set_operator("wm.sticky_asset_browser")
            op.ui_button = True
            self.asset_gizmo = mpr
        except Exception as e:
            print(f"Error in StickyAssetBrowser_UI_Button.setup: {e}")


classes = (
    AssetBrowserSettings,
    StickyAssetBrowserPreferences,
    StickyAssetBrowser,
    StickyAssetBrowser_UI_Button
)

def register():
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(f"Error registering class {cls.__name__}: {e}")
    # Additional setup, e.g., adding properties
    try:
        bpy.types.Scene.asset_browser_settings = bpy.props.PointerProperty(type=AssetBrowserSettings)
    except Exception as e:
        print(f"Error setting Scene.asset_browser_settings: {e}")

def unregister():
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering class {cls.__name__}: {e}")
    # Clean up additional setup
    try:
        if hasattr(bpy.types.Scene, 'asset_browser_settings'):
            del bpy.types.Scene.asset_browser_settings
    except Exception as e:
        print(f"Error removing Scene.asset_browser_settings: {e}")


if __name__ == "__main__":
    register()