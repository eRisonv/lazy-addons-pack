bl_info = {
    "name": "Fast Project Creator",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "Status Bar > New Project Icon",
    "description": "Creates a project folder structure, collections, saves blend file, and opens folder in Explorer",
    "category": "3D View",
}

import bpy
import os
import subprocess
from bpy.types import Operator, Panel, AddonPreferences
from bpy.props import StringProperty

class FASTPROJECT_AddonPreferences(AddonPreferences):
    """Addon preferences for Fast Project Creator."""
    bl_idname = __name__

    base_directory: StringProperty(
        name="Base Directory",
        description="Default directory where projects will be created",
        default=r"D:\My Blender",
        subtype='DIR_PATH'
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Fast Project Creator Settings:")
        layout.prop(self, "base_directory")

class FASTPROJECT_OT_CreateProject(Operator):
    bl_idname = "fastproject.create_project"
    bl_label = "Start New Project"
    bl_description = "Create a new project with folder structure and collections"

    project_name: StringProperty(
        name="Project Name",
        description="Enter the name for the new project",
        default=""
    )

    def get_base_directory(self, context):
        """Get the base directory from addon preferences."""
        addon_prefs = context.preferences.addons[__name__].preferences
        return addon_prefs.base_directory

    def get_unique_project_path(self, base_dir, project_name):
        """Generate a unique project path by appending _1, _2, etc. if needed."""
        base_path = os.path.join(base_dir, project_name)
        if not os.path.exists(base_path):
            return project_name, base_path
        
        counter = 1
        while True:
            new_name = f"{project_name}_{counter}"
            new_path = os.path.join(base_dir, new_name)
            if not os.path.exists(new_path):
                return new_name, new_path
            counter += 1

    def create_collections(self, context, project_name):
        """Create a parent collection with the project name and child collections inside it."""
        child_collections = [
            ("Blockout", "COLOR_04"),  # Green
            ("High Poly", "COLOR_05"), # Blue
            ("Low Poly", "COLOR_06")   # Pink
        ]
        
        # Проверяем, существует ли родительская коллекция с именем проекта
        parent_coll = bpy.data.collections.get(project_name)
        if not parent_coll:
            # Если нет, создаем новую родительскую коллекцию
            parent_coll = bpy.data.collections.new(project_name)
            # Связываем родительскую коллекцию со сценой
            context.scene.collection.children.link(parent_coll)
        
        # Создаем или получаем дочерние коллекции и связываем их с родительской
        for coll_name, color_tag in child_collections:
            child_coll = bpy.data.collections.get(coll_name)
            if not child_coll:
                child_coll = bpy.data.collections.new(coll_name)
                child_coll.color_tag = color_tag
            # Связываем дочернюю коллекцию с родительской, если еще не связана
            if child_coll.name not in parent_coll.children:
                parent_coll.children.link(child_coll)

    def save_blend_file(self, project_path, project_name):
        """Save the current blend file in the Model folder with project name."""
        model_folder = os.path.join(project_path, "Model")
        blend_file_path = os.path.join(model_folder, f"{project_name}.blend")
        
        try:
            # Сохраняем blend файл
            bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)
            return True, blend_file_path
        except Exception as e:
            return False, str(e)

    def execute(self, context):
        if not self.project_name:
            self.report({'ERROR'}, "Project name cannot be empty!")
            return {'CANCELLED'}

        # Get base directory from preferences
        BASE_DIR = self.get_base_directory(context)
        
        # Check if base directory exists
        if not os.path.exists(BASE_DIR):
            self.report({'ERROR'}, f"Base directory does not exist: {BASE_DIR}")
            return {'CANCELLED'}
        
        folders = ["Reference", "Model", "Baking", "Textures", "Render"]

        try:
            # Get unique project name and path
            final_project_name, project_path = self.get_unique_project_path(BASE_DIR, self.project_name)

            # Create main project folder
            os.makedirs(project_path, exist_ok=True)
            
            # Create subfolders
            for folder in folders:
                os.makedirs(os.path.join(project_path, folder), exist_ok=True)
            
            # Create collections in Blender with the project name
            self.create_collections(context, final_project_name)
            
            # Save blend file in Model folder
            save_success, save_result = self.save_blend_file(project_path, final_project_name)
            
            if save_success:
                self.report({'INFO'}, f"Project '{final_project_name}' created and blend file saved at: {save_result}")
            else:
                self.report({'WARNING'}, f"Project '{final_project_name}' created but failed to save blend file: {save_result}")
            
            # Open the project folder in Windows Explorer
            subprocess.run(["explorer", project_path])
            
            return {'FINISHED'}
        
        except Exception as e:
            self.report({'ERROR'}, f"Error creating project: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def draw_status_bar_button(self, context):
    """Draw the New Project button in the Status Bar."""
    layout = self.layout
    layout.separator()
    layout.operator("fastproject.create_project", text="New Project", icon='FILE_NEW')

def register():
    bpy.utils.register_class(FASTPROJECT_AddonPreferences)
    bpy.utils.register_class(FASTPROJECT_OT_CreateProject)
    
    # Add button to Status Bar
    bpy.types.STATUSBAR_HT_header.append(draw_status_bar_button)

def unregister():
    # Remove button from Status Bar
    bpy.types.STATUSBAR_HT_header.remove(draw_status_bar_button)
    
    bpy.utils.unregister_class(FASTPROJECT_OT_CreateProject)
    bpy.utils.unregister_class(FASTPROJECT_AddonPreferences)

if __name__ == "__main__":
    register()