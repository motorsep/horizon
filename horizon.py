"""  
 * This program is free software: you can redistribute it and/or modify  
 * it under the terms of the GNU General Public License as published by  
 * the Free Software Foundation, version 2.
 *
 * This program is distributed in the hope that it will be useful, but 
 * WITHOUT ANY WARRANTY; without even the implied warranty of 
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License 
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

# Horizon Add-on for Blender
# This script creates a custom tab "Horizon" in the 3D View's N-panel (right sidebar).
# It includes scaling tools, material cleanup, geo removal, and additional utilities.
# Useful when working between Trenchbroom level editor and Blender, with target output being FBX/OBJ for modern game engines

import bpy
import bmesh

bl_info = {
    "name": "Horizon Add-on",
    "author": "motorsep, Grok",
    "version": (1, 6),
    "blender": (4, 0, 0),
    "location": "3D View > N-Panel > Horizon Tab",
    "description": "Adds a Horizon tab with various mesh editing tools",
    "category": "3D View",
}

class HorizonScaleUpOperator(bpy.types.Operator):
    """Operator to scale up selected objects by the factor"""
    bl_idname = "horizon.scale_up"
    bl_label = "Scale Up"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        factor = context.scene.horizon_scale_factor
        if factor <= 0.0:
            return {'CANCELLED'}
        
        selected_objs = context.selected_objects
        if not selected_objs:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}
        
        # Scale up
        bpy.ops.transform.resize(value=(factor, factor, factor))
        
        # Apply scale to each selected object
        active_obj = context.active_object
        for obj in selected_objs:
            context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Restore active object
        context.view_layer.objects.active = active_obj
        
        return {'FINISHED'}

class HorizonScaleDownOperator(bpy.types.Operator):
    """Operator to scale down selected objects by the factor"""
    bl_idname = "horizon.scale_down"
    bl_label = "Scale Down"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        factor = context.scene.horizon_scale_factor
        if factor <= 0.0:
            return {'CANCELLED'}
        
        selected_objs = context.selected_objects
        if not selected_objs:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}
        
        # Scale down (divide)
        bpy.ops.transform.resize(value=(1/factor, 1/factor, 1/factor))
        
        # Apply scale to each selected object
        active_obj = context.active_object
        for obj in selected_objs:
            context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Restore active object
        context.view_layer.objects.active = active_obj
        
        return {'FINISHED'}

class HorizonCleanUpMatsOperator(bpy.types.Operator):
    """Operator to clean up materials on selected meshes"""
    bl_idname = "horizon.clean_up_mats"
    bl_label = "Clean Up Mats"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefix = context.scene.horizon_mat_prefix
        suffix = context.scene.horizon_mat_suffix
        
        selected_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objs:
            self.report({'WARNING'}, "No meshes selected")
            return {'CANCELLED'}
        
        active_obj = context.active_object
        to_remove = ["models/DefaultMaterial.vertex", "textures/__TB_empty.vertex"]
        
        for obj in selected_objs:
            context.view_layer.objects.active = obj
            
            # Collect slots to remove
            slots_to_remove = []
            for i, slot in enumerate(obj.material_slots):
                if slot.material and slot.material.name in to_remove:
                    slots_to_remove.append(i)
            
            # Remove in reverse order
            for i in sorted(slots_to_remove, reverse=True):
                obj.active_material_index = i
                bpy.ops.object.material_slot_remove()
            
            # Process remaining materials
            for slot in obj.material_slots:
                if slot.material:
                    mat_name = slot.material.name
                    if mat_name.startswith(prefix):
                        stripped = mat_name[len(prefix):]
                        if stripped.endswith(suffix):
                            extracted = stripped[:-len(suffix)]
                        else:
                            extracted = stripped
                        existing_mat = bpy.data.materials.get(extracted)
                        if existing_mat:
                            slot.material = existing_mat
                        else:
                            slot.material.name = extracted
        
        # Restore active object
        context.view_layer.objects.active = active_obj
        
        return {'FINISHED'}

class HorizonRemoveGeoOperator(bpy.types.Operator):
    """Operator to remove faces with the selected material from selected meshes"""
    bl_idname = "horizon.remove_geo"
    bl_label = "Remove Geo"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mat = context.scene.horizon_remove_material
        if not mat:
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}
        
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_meshes:
            self.report({'WARNING'}, "No meshes selected")
            return {'CANCELLED'}
        
        active_obj = context.active_object
        
        for obj in selected_meshes:
            context.view_layer.objects.active = obj
            
            # Find slot indices with this material
            slot_indices = [i for i, slot in enumerate(obj.material_slots) if slot.material == mat]
            if not slot_indices:
                continue
            
            # Enter edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Deselect all
            bpy.ops.mesh.select_all(action='DESELECT')
            
            # Use bmesh to select faces
            mesh = bmesh.from_edit_mesh(obj.data)
            for face in mesh.faces:
                if face.material_index in slot_indices:
                    face.select = True
            
            # Update and delete
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.mesh.delete(type='FACE')
            
            # Back to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Restore active object
        context.view_layer.objects.active = active_obj
        
        return {'FINISHED'}

class HorizonRemoveVertGroupsOperator(bpy.types.Operator):
    """Operator to remove all vertex groups from selected meshes"""
    bl_idname = "horizon.remove_vert_groups"
    bl_label = "Remove Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_meshes:
            self.report({'WARNING'}, "No meshes selected")
            return {'CANCELLED'}
        
        active_obj = context.active_object
        
        for obj in selected_meshes:
            context.view_layer.objects.active = obj
            while obj.vertex_groups:
                obj.vertex_groups.remove(obj.vertex_groups[0])
        
        context.view_layer.objects.active = active_obj
        return {'FINISHED'}

class HorizonRemoveCustPropsOperator(bpy.types.Operator):
    """Operator to remove all custom properties from selected objects"""
    bl_idname = "horizon.remove_cust_props"
    bl_label = "Remove Custom Props"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objs = context.selected_objects
        if not selected_objs:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}
        
        active_obj = context.active_object
        
        for obj in selected_objs:
            context.view_layer.objects.active = obj
            keys = list(obj.keys())
            for key in keys:
                if key not in ['_RNA_UI']:  # Avoid removing internal props
                    del obj[key]
        
        context.view_layer.objects.active = active_obj
        return {'FINISHED'}

class HorizonTriangulateModOperator(bpy.types.Operator):
    """Operator to add Triangulate modifier with specific settings to selected objects"""
    bl_idname = "horizon.triangulate_mod"
    bl_label = "Triangulate Mod"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objs:
            self.report({'WARNING'}, "No meshes selected")
            return {'CANCELLED'}
        
        active_obj = context.active_object
        
        for obj in selected_objs:
            context.view_layer.objects.active = obj
            mod = obj.modifiers.new(name="Triangulate", type='TRIANGULATE')
            mod.quad_method = 'BEAUTY'
            mod.ngon_method = 'BEAUTY'
            mod.keep_custom_normals = True
        
        context.view_layer.objects.active = active_obj
        return {'FINISHED'}

class HorizonPanel(bpy.types.Panel):
    """Creates the Horizon panel in the 3D View N-panel"""
    bl_label = "Horizon"
    bl_idname = "VIEW3D_PT_horizon"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Horizon"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "horizon_scale_factor", text="Scale Factor")
        
        row = layout.row()
        row.operator("horizon.scale_up", text="Scale Up")
        row.operator("horizon.scale_down", text="Scale Down")
        
        layout.prop(context.scene, "horizon_mat_prefix", text="Mat Prefix")
        layout.prop(context.scene, "horizon_mat_suffix", text="Mat Suffix")
        
        layout.operator("horizon.clean_up_mats", text="Clean Up Mats")
        
        layout.prop(context.scene, "horizon_remove_material", text="Material to Remove")
        layout.operator("horizon.remove_geo", text="Remove Geo")
        
        layout.operator("horizon.remove_vert_groups", text="Remove Vert Groups")
        layout.operator("horizon.remove_cust_props", text="Remove Cust Props")
        layout.operator("horizon.triangulate_mod", text="Triangulate Mod")

def register():
    bpy.types.Scene.horizon_scale_factor = bpy.props.FloatProperty(
        name="Scale Factor",
        description="Factor to scale by (positive value > 0)",
        default=26.8364,
        min=0.0,
        unit='LENGTH'
    )
    bpy.types.Scene.horizon_mat_prefix = bpy.props.StringProperty(
        name="Material Prefix",
        description="Prefix for material names to extract",
        default="textures/atrium/"
    )
    bpy.types.Scene.horizon_mat_suffix = bpy.props.StringProperty(
        name="Material Suffix",
        description="Suffix for material names to extract",
        default=".vertex"
    )
    bpy.types.Scene.horizon_remove_material = bpy.props.PointerProperty(
        name="Material to Remove",
        description="Select a material to remove geometry using it",
        type=bpy.types.Material
    )
    bpy.utils.register_class(HorizonScaleUpOperator)
    bpy.utils.register_class(HorizonScaleDownOperator)
    bpy.utils.register_class(HorizonCleanUpMatsOperator)
    bpy.utils.register_class(HorizonRemoveGeoOperator)
    bpy.utils.register_class(HorizonRemoveVertGroupsOperator)
    bpy.utils.register_class(HorizonRemoveCustPropsOperator)
    bpy.utils.register_class(HorizonTriangulateModOperator)
    bpy.utils.register_class(HorizonPanel)

def unregister():
    bpy.utils.unregister_class(HorizonPanel)
    bpy.utils.unregister_class(HorizonTriangulateModOperator)
    bpy.utils.unregister_class(HorizonRemoveCustPropsOperator)
    bpy.utils.unregister_class(HorizonRemoveVertGroupsOperator)
    bpy.utils.unregister_class(HorizonRemoveGeoOperator)
    bpy.utils.unregister_class(HorizonCleanUpMatsOperator)
    bpy.utils.unregister_class(HorizonScaleDownOperator)
    bpy.utils.unregister_class(HorizonScaleUpOperator)
    del bpy.types.Scene.horizon_remove_material
    del bpy.types.Scene.horizon_mat_suffix
    del bpy.types.Scene.horizon_mat_prefix
    del bpy.types.Scene.horizon_scale_factor

if __name__ == "__main__":
    register()