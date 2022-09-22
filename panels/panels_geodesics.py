import bpy


from GenericMarkerCreator28.operators.geodesic_operators import GeodesicPaths, GeodesicCutterWithLandmarks

class GeodesicsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_genericlandmarks_geodesics";
    bl_label = "Geodesics";
    bl_context = "objectmode";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_category = "Generic-Landmarks";
    bl_description = "Geodesic path based utilities";


    def draw(self, context):
        if(context.active_object):
            if(context.active_object.type != 'MESH'):
                return
            layout = self.layout
            box = layout.box()
            box.label(text='Geodesic Surface Paths')
            row = box.row();
            row.operator(GeodesicPaths.bl_idname);

            box = layout.box()
            box.label(text='Landmark Seams')
            row = box.row();
            geo_seams_op = row.operator(GeodesicCutterWithLandmarks.bl_idname);

            row = box.row()
            row.prop( context.active_object, 'geodesics_show_landmark_seams')
            geo_seams_op.show_seams = context.active_object.geodesics_show_landmark_seams