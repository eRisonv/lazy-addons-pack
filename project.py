bl_info = {
    "name": "Fast Project Creator",
    "author": "Gwyn",
    "version": (1, 3),
    "blender": (2, 80, 0),
    "location": "Info Header > New Project Icon",
    "description": "Creates a project folder structure, collections, saves blend file, and opens folder in Explorer. Shift+Click opens current project folder",
    "category": "3D View",
}

import bpy
import os
import subprocess
from bpy.types import Operator, AddonPreferences
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

class FASTPROJECT_OT_OpenCurrentProject(Operator):
    bl_idname = "fastproject.open_current_project"
    bl_label = "Open Current Project Folder"
    bl_description = "Open the folder containing the current blend file in Windows Explorer"

    def execute(self, context):
        current_blend_path = bpy.data.filepath
        
        if not current_blend_path:
            self.report({'ERROR'}, "No blend file is currently saved. Please save your project first.")
            return {'CANCELLED'}
        
        project_folder = os.path.dirname(current_blend_path)
        
        if not os.path.exists(project_folder):
            self.report({'ERROR'}, f"Project folder does not exist: {project_folder}")
            return {'CANCELLED'}
        
        try:
            subprocess.run(["explorer", project_folder])
            self.report({'INFO'}, f"Opened project folder: {project_folder}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open project folder: {str(e)}")
            return {'CANCELLED'}

class FASTPROJECT_OT_CreateProject(Operator):
    bl_idname = "fastproject.create_project"
    bl_label = "Start New Project"
    bl_description = "Create a new project with folder structure and collections. Hold Shift to open current project folder instead"

    project_name: StringProperty(
        name="Project Name",
        description="Enter the name for the new project",
        default=""
    )

    def get_base_directory(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        return addon_prefs.base_directory

    def get_unique_project_path(self, base_dir, project_name):
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
        child_collections = [
            ("Blockout", "COLOR_04"),  # Green
            ("High Poly", "COLOR_05"), # Blue
            ("Low Poly", "COLOR_06")   # Pink
        ]
        
        parent_coll = bpy.data.collections.get(project_name)
        if not parent_coll:
            parent_coll = bpy.data.collections.new(project_name)
            context.scene.collection.children.link(parent_coll)
        
        for coll_name, color_tag in child_collections:
            child_coll = bpy.data.collections.get(coll_name)
            if not child_coll:
                child_coll = bpy.data.collections.new(coll_name)
                child_coll.color_tag = color_tag
            if child_coll.name not in parent_coll.children:
                parent_coll.children.link(child_coll)

    def save_blend_file(self, project_path, project_name):
        model_folder = os.path.join(project_path, "Model")
        blend_file_path = os.path.join(model_folder, f"{project_name}.blend")
        
        try:
            bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)
            return True, blend_file_path
        except Exception as e:
            return False, str(e)

    def execute(self, context):
        if not self.project_name:
            self.report({'ERROR'}, "Project name cannot be empty!")
            return {'CANCELLED'}

        BASE_DIR = self.get_base_directory(context)
        
        if not os.path.exists(BASE_DIR):
            self.report({'ERROR'}, f"Base directory does not exist: {BASE_DIR}")
            return {'CANCELLED'}
        
        folders = ["Reference", "Model", "Baking", "Textures", "Render"]

        try:
            final_project_name, project_path = self.get_unique_project_path(BASE_DIR, self.project_name)
            os.makedirs(project_path, exist_ok=True)
            
            for folder in folders:
                os.makedirs(os.path.join(project_path, folder), exist_ok=True)
            
            self.create_collections(context, final_project_name)
            
            save_success, save_result = self.save_blend_file(project_path, final_project_name)
            
            if save_success:
                self.report({'INFO'}, f"Project '{final_project_name}' created and blend file saved at: {save_result}")
            else:
                self.report({'WARNING'}, f"Project '{final_project_name}' created but failed to save blend file: {save_result}")
            
            subprocess.run(["explorer", project_path])
            
            return {'FINISHED'}
        
        except Exception as e:
            self.report({'ERROR'}, f"Error creating project: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        if event.shift:
            bpy.ops.fastproject.open_current_project()
            return {'FINISHED'}
        else:
            return context.window_manager.invoke_props_dialog(self)

def draw_project_buttons(self, context):
    """Draw the New Project button in the Header, similar to GoB."""
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)

        row.operator(
            operator="fastproject.create_project",
            text="New",
            emboss=True,
            icon='FILE_NEW'
        )

def register():
    bpy.utils.register_class(FASTPROJECT_AddonPreferences)
    bpy.utils.register_class(FASTPROJECT_OT_OpenCurrentProject)
    bpy.utils.register_class(FASTPROJECT_OT_CreateProject)
    
    # Append button to header
    bpy.types.TOPBAR_HT_upper_bar.append(draw_project_buttons)

def unregister():
    # Remove button from header
    bpy.types.TOPBAR_HT_upper_bar.remove(draw_project_buttons)
    
    bpy.utils.unregister_class(FASTPROJECT_OT_CreateProject)
    bpy.utils.unregister_class(FASTPROJECT_OT_OpenCurrentProject)
    bpy.utils.unregister_class(FASTPROJECT_AddonPreferences)

if __name__ == "__main__":
    register()