import bpy
from GenericMarkerCreator28.utils.staticutilities import getMeshForBlenderMarker;
from GenericMarkerCreator28.operators.spectraloperations import SpectralHKS, SpectralWKS, SpectralGISIF, SpectralShape, AddSpectralSignatures, AddSpectralSignatureLandmarks, SpectralFeatures, MeanCurvatures;


class SpectralGeneralPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_spectralpanel"
    bl_label = "Spectral Functions";
    bl_context = "objectmode";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_category = "Generic-Landmarks"
    bl_description = "Spectral functions for a discrete surface";
        
    def draw(self, context):
        if(context.active_object):
            if(context.active_object.type != 'MESH'):
                return;
            layout = self.layout;
            mainbox = layout.box();
            mainbox.label(text='Spectral Properties');
            
            row = mainbox.row();
            row.prop(context.active_object, 'spectral_sync');
            
            row = mainbox.row();
            row.prop(context.active_object, 'post_process_colors', text='Post Process Colors?');
            
            col = row.column();
            col.prop(context.active_object, 'post_process_min', text='Min');
            
            col = row.column();
            col.prop(context.active_object, 'post_process_max', text='Max');
            
            row = mainbox.row();
            row.prop(context.active_object, 'eigen_k');
            
            box = mainbox.box();
            box.label(text='Low Pass Filtering (Eigen Shapes)')
            row = box.row();
            row.prop(context.active_object, 'live_spectral_shape');
            row.operator(SpectralShape.bl_idname);           
            
            row = box.row();
            row.operator(SpectralFeatures.bl_idname);
            
            box = layout.box();
            box.label(text='Mean Curvatures')
            
            row = box.row();
            col = row.column();
            col.prop(context.active_object, 'mean_curvatures_use_normal');
            
            col = row.column();
            op = row.operator(MeanCurvatures.bl_idname);

class HKSPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_hksspanel"
    bl_label = "HKS Controls";
    bl_context = "objectmode";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_category = "Generic-Landmarks"
    bl_description = "Heat Kernel signature functions on a discrete surface";   
     
    def draw(self, context):
        if(context.active_object):
            if(context.active_object.type != 'MESH'):
                return;
            layout = self.layout;
            box = layout.box();
            box.label(text='HKS');
            row = box.row();       
            
            row.prop(context.active_object, 'hks_t');
            row.prop(context.active_object, 'hks_current_t');
            
            row = box.row();
            row.prop(context.active_object, 'hks_log_start');
            row.prop(context.active_object, 'hks_log_end');
            
            row.prop(context.active_object, 'live_hks');
            row = box.row();
            row.operator(SpectralHKS.bl_idname);

class WKSPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_wksspanel"
    bl_label = "WKS Controls";

    bl_context = "objectmode";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_category = "Generic-Landmarks"
    bl_description = "Wave Kernel signature functions on a discrete surface";
    
    def draw(self, context):
        if(context.active_object):
            if(context.active_object.type != 'MESH'):
                return;
            layout = self.layout;
            box = layout.box();
            box.label(text='WKS');
            row = box.row();       
            row.prop(context.active_object, 'wks_e');
            row.prop(context.active_object, 'wks_variance');
            row.prop(context.active_object, 'wks_current_e');
            row.prop(context.active_object, 'live_wks');
            row = box.row();
            row.operator(SpectralWKS.bl_idname);

class GISIFPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_gisifpanel"
    bl_label = "GISIF Controls";

    bl_context = "objectmode";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_category = "Generic-Landmarks"
    bl_description = "GISIF signature functions on a discrete surface";  
    
    def draw(self, context):
        if(context.active_object):
            if(context.active_object.type != 'MESH'):
                return;
            layout = self.layout;
            box = layout.box();
            box.label(text='GISIF');
            row = box.row();
            row.prop(context.active_object, 'gisif_threshold');
            row.prop(context.active_object, 'gisif_group_index');
            row.prop(context.active_object, 'live_gisif');
            
            box_linear = box.box();
            box_linear.label(text='Linear Combinations');
            row = box_linear.row();
            row.prop(context.active_object, 'linear_gisif_combinations');
            row = box_linear.row();
            row.prop(context.active_object, 'linear_gisif_n');
            
            row = box.row();
            row.label(text='GISIF:%s'%(context.active_object.gisif_group_name));
            row.prop(context.active_object, 'gisif_symmetries');
            row.prop(context.active_object, 'gisif_symmetry_index');
            row = box.row();
            row.operator(SpectralGISIF.bl_idname);
            
            kp_box = box.box();
            kp_box.label(text='Generate Keypoints');
            row = kp_box.row();
            row.prop(context.active_object, 'gisif_markers_n');                        
            row.operator(AddSpectralSignatureLandmarks.bl_idname);
            
            save_box = box.box();
            save_box.label(text='Save Signatures')
            row = save_box.row();
            row.prop(context.active_object, 'signatures_dir');
            row.operator(AddSpectralSignatures.bl_idname);