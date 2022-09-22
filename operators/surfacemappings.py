import bpy

class PanelHelpAddMappingFromFile(bpy.types.Operator):
    bl_idname = "genericlandmarks.panel_help_add_mapping_from_file";
    bl_label = "Add Mapping";
    bl_description = "Operator to help add a mapping entry that can be filled with details and constructed. Select two meshes in scene. Active Object gets the mapping from non-active object in selection";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_options = {'REGISTER', 'UNDO'};
    m1: bpy.props.StringProperty(name='m1', default="---");
    m2: bpy.props.StringProperty(name='m2', default="---");
    
    def execute(self, context):
        meshes = [m for m in context.selected_objects if m.type == 'MESH'];
        argument_meshes = [];
        try:
            argument_meshes = [context.scene.objects[self.m1], context.scene.objects[self.m2] ];
        except KeyError:
            pass;
                
        if(len(meshes) < 2 and len(argument_meshes) <2 ):
            self.report({'WARNING'}, "Select two meshes from the scene");
            return {'FINISHED'};
        if(len(argument_meshes) > 1):
            meshes = argument_meshes;
            
        m1, m2 = meshes[0], meshes[1];
        
        if(m1 == context.active_object):
            s = m1;
            t = m2;
        else:
            s = m2;
            t = m1;
        
        map = s.surfacemappings.add();
        map.map_to_mesh = t.name;
        map.apply_on_duplicate = True;
        map.mapping_name = 'Mapping';        
        return {'FINISHED'};   

class PanelHelpRemoveMappingFromFile(bpy.types.Operator):
    bl_idname = "genericlandmarks.panel_help_remove_mapping_from_file";
    bl_label = "Remove Last Mapping";
    bl_description = "Operator to help remove a mapping entry for the selected mesh";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_options = {'REGISTER', 'UNDO'};
    currentobject: bpy.props.StringProperty(name='currentobject', default="---");
    
    def execute(self, context):
        mesh = None;
        try:            
            mesh = bpy.data.objects[self.currentobject];
        except:
            mesh = context.active_object;
            
        if(not mesh):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;
        
        if(not mesh.type in {"MESH"}):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;        
        
        mesh.surfacemappings.remove( len(mesh.surfacemappings) - 1 );        
        return {'FINISHED'};
    
class PanelHelpClearMappingFromFile(bpy.types.Operator):
    bl_idname = "genericlandmarks.panel_help_clear_mapping_from_file";
    bl_label = "Clear All Mappings";
    bl_description = "Operator to help clear all mapping entries for the selected mesh";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";    
    bl_context = "objectmode";
    bl_options = {'REGISTER', 'UNDO'};
    currentobject: bpy.props.StringProperty(name='currentobject', default="---");
    
    def execute(self, context):
        mesh = None;
        try:            
            mesh = bpy.data.objects[self.currentobject];
        except:
            mesh = context.active_object;
            
        if(not mesh):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;
        
        if(not mesh.type in {"MESH"}):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;        
        
        mesh.surfacemappings.clear();
        return {'FINISHED'};

class PanelHelpConstructMappingFromFile(bpy.types.Operator):
    bl_idname = "genericlandmarks.panel_help_construct_mapping_from_file";
    bl_label = "Construct Mapping";
    bl_description = "Operator to construct a mapping given the index and the mesh name";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_options = {'REGISTER', 'UNDO'};
    current_object: bpy.props.StringProperty(name='currentobject', default="---");
    mapping_index: bpy.props.IntProperty(name='Mapping Index', default=0);
    
    def execute(self, context):
        mesh = None;
        try:            
            mesh = bpy.data.objects[self.currentobject];
        except:
            mesh = context.active_object;
            
        if(not mesh):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;
        
        if(not mesh.type in {"MESH"}):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;        
        
        print(self.mapping_index, self.current_object, mesh.surfacemappings[self.mapping_index].mapping_name);
        
#         try:
        mapping = mesh.surfacemappings[self.mapping_index];
        mapping.constructMapping();
#         except IndexError:
#             self.report({'WARNING'}, "No valid Mapping");
                
        return {'FINISHED'};
class PanelHelpExportMappingFromFile(bpy.types.Operator):
    bl_idname = "genericlandmarks.panel_help_export_mapping_from_file";
    bl_label = "Export  Mapping";
    bl_description = "Operator to export a mapping (format: v1, v2, v3, u, v, w) given the index and the mesh name";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_options = {'REGISTER', 'UNDO'};
    current_object: bpy.props.StringProperty(name='currentobject', default="---");
    mapping_index: bpy.props.IntProperty(name='Mapping Index', default=0);
    
    def execute(self, context):
        mesh = None;
        try:            
            mesh = bpy.data.objects[self.currentobject];
        except:
            mesh = context.active_object;
            
        if(not mesh):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;
        
        if(not mesh.type in {"MESH"}):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;        
        
        print(self.mapping_index, self.current_object);
        
        try:
            mapping = mesh.surfacemappings[self.mapping_index];
            mapping.exportMapping();
        except IndexError:
            self.report({'WARNING'}, "No valid Mapping");
                
        return {'FINISHED'};
    
class PanelHelpDeformationMappingFromFile(bpy.types.Operator):
    bl_idname = "genericlandmarks.panel_help_deformation_mapping_from_file";
    bl_label = "Deform  Mapping";
    bl_description = "Operator to deform to the shape using a mapping given the index and the mesh name";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_options = {'REGISTER', 'UNDO'};
    current_object: bpy.props.StringProperty(name='currentobject', default="---");
    mapping_index: bpy.props.IntProperty(name='Mapping Index', default=0);
    
    def execute(self, context):
        mesh = None;
        try:            
            mesh = bpy.data.objects[self.currentobject];
        except:
            mesh = context.active_object;
            
        if(not mesh):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;
        
        if(not mesh.type in {"MESH"}):
            self.report({'WARNING'}, "Select a mesh from the scene");
            return;        
        
        print(self.mapping_index, self.current_object);
        
        try:
            mapping = mesh.surfacemappings[self.mapping_index];      
            mapping.deformWithMapping();
        except IndexError:
            self.report({'WARNING'}, "No valid Mapping");
                
        return {'FINISHED'};