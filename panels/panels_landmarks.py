import bpy


from GenericMarkerCreator28.utils.staticutilities import getMeshForBlenderMarker
from GenericMarkerCreator28.operators.landmarkspair import AssignMeshPair
from GenericMarkerCreator28.operators.landmarksliveoperators import LiveLandmarksCreator
from GenericMarkerCreator28.operators.landmarkscreator import CreateLandmarks, ReorderLandmarks, \
ChangeLandmarks, UnLinkLandmarks, LinkLandmarks, RemoveLandmarks, LandmarkStatus, LandmarksPairFinder, TransferLandmarkNames, AutoLinkLandmarksByID, SnapLandmarksToVertex, \
LoadBIMLandmarks, TransferLandmarks

class Landmarks(bpy.types.Panel):
    bl_idname = "OBJECT_PT_genericlandmarks_landmarks";
    bl_label = "Landmarks";
    bl_context = "objectmode";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_category = "Generic-Landmarks";
    bl_description = "Create landmarks or markers on the mesh";

    def draw(self, context):        
        if(context.active_object):
            if(context.active_object.type != 'MESH'):
                return;
            layout = self.layout;
            box = layout.box();
            box.label(text='Global properties');
            row = box.row();
            row.prop(context.scene, 'use_mirrormode_x');
            row.prop(context.scene, 'landmarks_use_selection');
            
            row = box.row();
            row.prop(context.active_object, 'snap_landmarks');
            
            row = box.row();
            row.prop(context.active_object, 'unlinked_landmark_color');
            
            box = layout.box();
            box.label(text='Load Landmarks from a file');
            
            row = box.row(align=True);
            col = row.column(align=True);
            col.prop(context.active_object, 'landmarks_file');
            
            col = row.column(align=True);
            col.operator(LoadBIMLandmarks.bl_idname);
            
            row = box.row();
            row.operator(TransferLandmarks.bl_idname);
            
            box = layout.box();
            box.label(text='Unpaired mesh operations');

            # if(len(context.active_object.generic_landmarks)):
            row = box.row();
            row.prop(context.active_object, 'hide_landmarks');
            
            row = box.row();
            op = row.operator(CreateLandmarks.bl_idname, text="Update Positions");
            op.updatepositions = True;
            
            row = box.row();
            row.operator(ChangeLandmarks.bl_idname);
            
            row = box.row();
            row.operator(ReorderLandmarks.bl_idname);
            
            row = box.row();
            row.operator(LiveLandmarksCreator.bl_idname);     

            box = layout.box()
            box.label(text='Snap Landmarks')
            row = box.row()
            op = row.operator(SnapLandmarksToVertex.bl_idname);
            row = box.row()
            row.prop(context.active_object, 'snap_landmarks_apply_on_duplicate', toggle=True)
            row.prop(context.active_object, 'snap_landmarks_create_vertices', toggle=True) 

            op.apply_on_duplicate = context.active_object.snap_landmarks_apply_on_duplicate
            op.create_vertices = context.active_object.snap_landmarks_create_vertices
                
                
            if(context.active_object.mapped_mesh):            
                box = layout.box();
                box.label(text='Mesh with a pair operations');              
                
                row = box.row();
                row.prop(context.active_object, 'linked_landmark_color');                
                
                row = box.row();
                row.operator(LandmarkStatus.bl_idname);
                
                row = box.row();
                row.operator(TransferLandmarkNames.bl_idname);
                
                row = box.row();
                row.operator(LandmarksPairFinder.bl_idname);

                box = layout.box();
                box.label(text='Mapped Mesh Operations')
                row = box.row();
                row.operator(AutoLinkLandmarksByID.bl_idname);

            if(context.active_object.is_visual_landmark):
                box = layout.box();
                box.label(text='Global Landmark settings');
                
                row = box.row();
                row.prop(context.active_object, 'edit_landmark_name');
                
                row = box.row();
                row.operator(RemoveLandmarks.bl_idname);
                
                belongs_to = getMeshForBlenderMarker(context.active_object);       
                if(belongs_to.is_landmarked_mesh):
                    box = layout.box();
                    box.label(text='Mesh Paired Landmark settings');
                    
                    row = box.row();
                    row.operator(LinkLandmarks.bl_idname);
                    
                    row = box.row();
                    row.operator(UnLinkLandmarks.bl_idname);  