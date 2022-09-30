import bpy

from GenericMarkerCreator28.utils.staticutilities import getMarkerOwner, getGenericLandmark;
from GenericMarkerCreator28.datatypes.bl_dtypes import GenericLandmark, GenericPointSignature, VertexToSurfaceMapping, VertexToSurfaceMappingBVH

def checkObjectsInScene(scene):
    orphanmarkers = []
    for o in scene.objects:
        if(o.type == 'MESH' and o.is_visual_landmark):
            parentmesh = scene.objects.get(o.belongs_to, None)
            if(not parentmesh):
                orphanmarkers.append(o)
    print('TOTAL ORPHAN MARKERS ', len(orphanmarkers))
    if(len(orphanmarkers)):
        bpy.ops.object.select_all(action='DESELECT')
        for o in orphanmarkers:
            if(o):
                o.hide_viewport = False
                o.hide_set(False)
                o.select_set(True)
        
        bpy.ops.object.delete()

def updateMeanCurvatures(self, context):
    if(self.post_process_colors):
        bpy.ops.genericlandmarks.meancurvatures('EXEC_DEFAULT', currentobject=self.name);

def hasValueChanged(o, key, value):
    try:
        print('SELF: %s, KEY: %s, CURRENT : %s, NEW : %s'%(o, key, o[key], value));
        return (o[key] != value);
    except KeyError:
        return True;

def get_hks_t(self):
    try:
        return self['hks_t'];
    except KeyError:
        return 0;
def set_hks_t(self, value):
    flag = hasValueChanged(self, 'hks_t', value);
    if(flag):
        self['hks_t'] = value;        
        if(self.live_hks):
            bpy.ops.genericlandmarks.spectralhks('EXEC_DEFAULT', currentobject=self.name);

def get_hks_current_t(self):
    try:
        return self['hks_current_t'];
    except KeyError:
        return 0;
def set_hks_current_t(self, value):
    if(hasValueChanged(self, 'hks_current_t', value)):
        self['hks_current_t'] = value;
        if(self.live_hks):
            bpy.ops.genericlandmarks.spectralhks('EXEC_DEFAULT', currentobject=self.name);

def get_hks_log_start(self):
    try:
        return self['hks_log_start'];
    except KeyError:
        return 1e-4;
def set_hks_log_start(self, value):
    if(hasValueChanged(self, 'hks_log_start', value)):
        self['hks_log_start'] = value;    
        if(self.live_hks):
            bpy.ops.genericlandmarks.spectralhks('EXEC_DEFAULT', currentobject=self.name);

def get_hks_log_end(self):
    try:
        return self['hks_log_end'];
    except KeyError:
        return 1.0;
def set_hks_log_end(self, value):
    if(hasValueChanged(self, 'hks_log_end', value)):
        self['hks_log_end'] = value;
        if(self.live_hks):
            bpy.ops.genericlandmarks.spectralhks('EXEC_DEFAULT', currentobject=self.name);

def updateSpectralProperty(self, context):
#     print('WHO AM I : ', self);
    if(self.spectral_soft_update):
        return;
    if(self.live_hks):
        bpy.ops.genericlandmarks.spectralhks('EXEC_DEFAULT', currentobject=self.name);
    elif(self.live_wks):
        bpy.ops.genericlandmarks.spectralwks('EXEC_DEFAULT', currentobject=self.name);
    elif(self.live_spectral_shape):
        bpy.ops.genericlandmarks.spectralshape('EXEC_DEFAULT', currentobject=self.name);
    elif(self.live_gisif):
        bpy.ops.genericlandmarks.spectralgisif('EXEC_DEFAULT', currentobject=self.name);

def get_marker_meshes(self, context):
    templatenames = ["_marker","_joint","_bone","_lines","_cloud"];
    return [(item.name, item.name, item.name) for item in bpy.data.objects if item.type == "MESH" and (not any(word in item.name for word in templatenames) and 'template_mkr_' in item.name)];

def changeMarkerColor(mesh, bmarker = None):    
    try:
        material = bpy.data.materials[mesh.name+'_LinkedMaterial'];
    except:
        material = bpy.data.materials.new(mesh.name+'_LinkedMaterial');
    
    material.diffuse_color = (mesh.linked_landmark_color[0], mesh.linked_landmark_color[1], mesh.linked_landmark_color[2], 1.0);
    material.specular_color = (mesh.linked_landmark_color[0], mesh.linked_landmark_color[1], mesh.linked_landmark_color[2]);
    
    if(bmarker):
        bmarker.data.materials.clear();
        bmarker.data.materials.append(material);
    
    return material;
    
def changeUnlinkedMarkerColor(mesh = None, bmarker = None):    
    try:
        material = bpy.data.materials[mesh.name+'_UnlinkedMaterial'];
    except:
        material = bpy.data.materials.new(mesh.name+'_UnlinkedMaterial');
    
    material.diffuse_color = (mesh.unlinked_landmark_color[0], mesh.unlinked_landmark_color[1], mesh.unlinked_landmark_color[2], 1.0);
    material.specular_color = (mesh.unlinked_landmark_color[0], mesh.unlinked_landmark_color[1], mesh.unlinked_landmark_color[2]);
    
    if(bmarker):
        bmarker.data.materials.clear();
        bmarker.data.materials.append(material);
    
    return material;
    
def updateNormalMarkerColor(self, context):
    changeMarkerColor(context.active_object);

def updateUnlinkedMarkerColor(self, context):
    changeUnlinkedMarkerColor(context.active_object);

def getLandmarkName(self):
#     print('WHO AM I : ', self);
    mesh, isM, isN = getMarkerOwner(self);
    if(mesh):
        data_landmark = getGenericLandmark(mesh, self);
        if(data_landmark):
            return data_landmark.landmark_name;
    
    return "No Name";

def setLandmarkName(self, value):
    mesh, isM, isN = getMarkerOwner(self);
    if(mesh):
        data_landmark = getGenericLandmark(mesh, self);
        if(data_landmark):
            data_landmark.landmark_name = value;
    
    self['edit_landmark_name'] = value;

def showHideConstraints(self, context):
    bpy.ops.genericlandmarks.createlandmarks('EXEC_DEFAULT',hidemarkers=True, currentobject = self.name);

def registration_landmarks(delete=False):
    if(not delete):
        bpy.types.Object.snap_landmarks = bpy.props.BoolProperty(name="Snap Landmarks", description="Flag to enable/disable snapping", default=False);
        bpy.types.Object.snap_landmarks_apply_on_duplicate = bpy.props.BoolProperty(name="Use Duplicated Mesh", description="Flag to use duplicated mesh instead of modifying the original mesh", default=False);
        bpy.types.Object.snap_landmarks_create_vertices = bpy.props.BoolProperty(name="Create Vertices", description="Flag to create vertices at landmark locations instead of moving them to the closest barycentric vertex", default=False);

        bpy.types.Object.is_landmarked_mesh = bpy.props.BoolProperty(name="Is Landmarked Mesh", description="Flag to identify meshes with landmarks", default=False);
        bpy.types.Object.hide_landmarks = bpy.props.BoolProperty(name="Hide Landmarks", description="Flag to show or hide landmarks in a mesh", default=False, update=showHideConstraints);
        bpy.types.Object.is_visual_landmark = bpy.props.BoolProperty(name="Is Visual Landmark", description="Flag to identify if the mesh is an object used for showing a landmark visually", default=False);
        bpy.types.Object.edit_landmark_name = bpy.props.StringProperty(name="Edit Landmark Name", description="Change Landmark name", default="No Name", set=setLandmarkName, get=getLandmarkName);#, update=updateLandmarkName);
        bpy.types.Object.belongs_to = bpy.props.StringProperty(name="Belongs To", description="The name of the mesh to which the landmark has been added", default="---");#, update=updateLandmarkName);

        bpy.types.Object.linked_landmark_color = bpy.props.FloatVectorProperty(name = "Landmark Color",subtype='COLOR',default=[0.0,1.0,0.0], description = "Color of a linked landmark",update=updateNormalMarkerColor);    
        bpy.types.Object.unlinked_landmark_color = bpy.props.FloatVectorProperty(name = "Unlinked Landmark Color",subtype='COLOR',default=[1.0,0.0,0.0],description = "The color of an unlinked landmark.", update=updateUnlinkedMarkerColor);
        
        bpy.types.Object.mapped_mesh = bpy.props.StringProperty(name="Mapped mesh",description="The Blender name of the mapped mesh on whom landmarks are linked",default="");
        
        bpy.types.Object.landmark_id = bpy.props.IntProperty(name = "Landmark Id",description = "The original id of a landmark",default = -1);
        bpy.types.Object.landmark_array_index = bpy.props.IntProperty(name = "Landmark Array Index",description = "The positional index of the marker in the array",default = -1);    
        bpy.types.Object.total_landmarks = bpy.props.IntProperty(name="Total Landmarks", description="Total number of landmarks for this mesh", default=0);
        bpy.types.Object.generic_landmarks = bpy.props.CollectionProperty(type=GenericLandmark);
        bpy.types.Object.landmarks_file = bpy.props.StringProperty(name="Landmarks File", 
                                                               description="Landmark file that contains the landmarks information as combination of faceid and barycentric coordinates or vertex indices with barycentric coordinaties", 
                                                               subtype="FILE_PATH", default="//");

        bpy.types.Scene.use_mirrormode_x = bpy.props.BoolProperty(name="Mirror Mode X", description="Use mirror mode on X-Axis", default=True);
        bpy.types.Scene.landmarks_use_selection = bpy.props.EnumProperty(name = "Landmarks List", items = get_marker_meshes, description = "Meshes available in the Blender scene to be used for as landmark mesh");

        bpy.types.Object.geodesics_show_landmark_seams = bpy.props.BoolProperty(name="Show Landmark Seams", description="If you have to show seams then use modal operator to show the seam paths", default=False)
        
        # if not checkObjectsInScene in bpy.app.handlers.depsgraph_update_post:
        #     bpy.app.handlers.depsgraph_update_post.append(checkObjectsInScene)
    else:

        # if checkObjectsInScene in bpy.app.handlers.depsgraph_update_post:
        #     bpy.app.handlers.depsgraph_update_post.remove(checkObjectsInScene)

        del bpy.types.Object.snap_landmarks
        del bpy.types.Object.snap_landmarks_apply_on_duplicate
        del bpy.types.Object.snap_landmarks_create_vertices

        del bpy.types.Object.is_landmarked_mesh
        del bpy.types.Object.hide_landmarks
        del bpy.types.Object.is_visual_landmark
        del bpy.types.Object.edit_landmark_name
        del bpy.types.Object.belongs_to
        del bpy.types.Object.linked_landmark_color
        del bpy.types.Object.unlinked_landmark_color
        del bpy.types.Object.mapped_mesh
        del bpy.types.Object.landmark_id
        del bpy.types.Object.landmark_array_index
        del bpy.types.Object.total_landmarks
        del bpy.types.Object.generic_landmarks
        del bpy.types.Object.landmarks_file

        del bpy.types.Scene.use_mirrormode_x
        del bpy.types.Scene.landmarks_use_selection

        del bpy.types.Object.geodesics_show_landmark_seams




def registration_spectral(delete=False):
    if(not delete):
        bpy.types.Object.spectral_soft_update = bpy.props.BoolProperty(name='Spectral Soft', description="flag to avoid update methods for spectral to run", default=False);
        bpy.types.Object.eigen_k = bpy.props.IntProperty(name="Eigen K", description="Number of Eigen Ranks to solve", default=5, min=1, step=1, update=updateSpectralProperty);
        bpy.types.Object.spectral_sync = bpy.props.BoolProperty(name='Spectral Sync', description="flag to sync spectral properties with paired mesh", default=False);
        
        
        bpy.types.Object.hks_t = bpy.props.FloatProperty(name="HKS Time", description="The time for which the heat dissipation for every point is calculated", default=20.0, min=0.1, update=updateSpectralProperty, get=get_hks_t, set=set_hks_t);
        bpy.types.Object.hks_current_t = bpy.props.IntProperty(name="HKS Current Time", description="The current time of heat dissipation", default=20, min=0, update=updateSpectralProperty, get=get_hks_current_t, set=set_hks_current_t);
        bpy.types.Object.hks_log_start = bpy.props.FloatProperty(name="HKS Log Start", description="The Log start value. A logspace is created between logstart and logend.", min=0.0, default=0.1, get=get_hks_log_start, set=set_hks_log_start, update=updateSpectralProperty);
        bpy.types.Object.hks_log_end = bpy.props.FloatProperty(name="HKS Log End", description="The Log end value. A logspace is created between logstart and logend.", min=0.0, default=10.0, get=get_hks_log_end, set=set_hks_log_end, update=updateSpectralProperty);
        
        bpy.types.Object.wks_e = bpy.props.IntProperty(name="WKS Evalautions", description="The Total evaluations for which WKS is calculated", default=100, min=2, step=1,update=updateSpectralProperty);
        bpy.types.Object.wks_current_e = bpy.props.IntProperty(name="WKS Current Evalaution", description="The current evaluation for which WKS is shown", default=0, min=0, step=1,update=updateSpectralProperty);
        bpy.types.Object.wks_variance = bpy.props.FloatProperty(name="WKS variance", description="The WKS variance to consider", default=6.0, min=0.00, update=updateSpectralProperty);
        
        bpy.types.Object.gisif_group_name = bpy.props.StringProperty(name='GISIF Group', description="The current GISIF Group and the clusters", default="");
        bpy.types.Object.gisif_group_index = bpy.props.IntProperty(name="GISIF Group", description="For a Threshold applied choose the GISIF Group to show", default=0, min=0, step=1,update=updateSpectralProperty);
        bpy.types.Object.gisif_threshold = bpy.props.FloatProperty(name="GISIF Threshold", description="The threshold for eigen values to group them as repeated", default=0.1, max=10000.0, min=0.0, update=updateSpectralProperty);
        
        bpy.types.Object.linear_gisif_combinations = bpy.props.BoolProperty(name='Linear GISIFS?', description="Use Linear GISIF combinations of gisifs from i to i+n", default=False, update=updateSpectralProperty);
        bpy.types.Object.linear_gisif_n = bpy.props.IntProperty(name='Linear GISIF (i+1)', description="Linear GISIF means combinations of gisifs from i to i+n", default=0, min=0, update=updateSpectralProperty);
        
        bpy.types.Object.gisif_symmetry_index = bpy.props.IntProperty(name='GISIF Symmetry Index', description="For the marker selected find the symmetrical gisifs", default=0, update=updateSpectralProperty);
        bpy.types.Object.gisif_markers_n = bpy.props.IntProperty(name='Spectral Clusters', description="With the computed Spectral signatures generate the lnadmarks for the count specified using GMM clustering", default=1, min=1);
        bpy.types.Object.gisif_symmetries = bpy.props.BoolProperty(name='GISIF Symmetries', description="Once the GISIFS are clustered add their symmetries also ", default=True);
        
        
        bpy.types.Object.live_hks = bpy.props.BoolProperty(name='Live HKS', description="Live HKS means reflect the changes in the scene immediately after values are changed (Eigen K or HKS Time)", default=False);
        bpy.types.Object.live_wks = bpy.props.BoolProperty(name='Live WKS', description="Live WKS means reflect the changes in the scene immediately after values are changed (Eigen K or HKS Time)", default=False);
        bpy.types.Object.live_spectral_shape = bpy.props.BoolProperty(name='Live Spectral Shape', description="Perform Live spectral shape", default=False);
        bpy.types.Object.live_gisif = bpy.props.BoolProperty(name='Live GISIF', description="Live GISIF means reflect the changes in the scene immediately after values are changed (Treshold or Group Index)", default=False);
        
        bpy.types.Object.post_process_colors = bpy.props.BoolProperty(name='Post Process Colors', description="Apply a postprocessing with histograms on the scalar values when visualized as colors", default=True);
        bpy.types.Object.post_process_min = bpy.props.FloatProperty(name='Post Process Min', description="Minimum Post processing value for histogram", default=0.1, min=0.0, max=1.0, step=0.01, precision=4, update=updateMeanCurvatures);
        bpy.types.Object.post_process_max = bpy.props.FloatProperty(name='Post Process Max', description="Apply a postprocessin on the scalar values when visualized as colors", default=0.9, min=0.0, max=1.0, step=0.01, precision=4, update=updateMeanCurvatures);
        
        bpy.types.Object.mean_curvatures_use_normal = bpy.props.BoolProperty(name='Normals Control Mean', description="Do Normals control mean curvatures?", default=True, update=updateMeanCurvatures);
        
        bpy.types.Object.signatures_dir = bpy.props.StringProperty(name="Directory Signatures", description="Directory where the signatures and the pca space is saved", subtype="DIR_PATH", default="//");
    
        bpy.types.Object.hks_signatures = bpy.props.CollectionProperty(type=GenericPointSignature);
        bpy.types.Object.wks_signatures = bpy.props.CollectionProperty(type=GenericPointSignature);
        bpy.types.Object.gisif_signatures = bpy.props.CollectionProperty(type=GenericPointSignature);
    
    else:
        del bpy.types.Object.spectral_soft_update
        del bpy.types.Object.eigen_k
        del bpy.types.Object.spectral_sync

        del bpy.types.Object.hks_t
        del bpy.types.Object.hks_current_t
        del bpy.types.Object.hks_log_start
        del bpy.types.Object.hks_log_end
        
        del bpy.types.Object.wks_e
        del bpy.types.Object.wks_current_e
        del bpy.types.Object.wks_variance
        
        del bpy.types.Object.gisif_group_name
        del bpy.types.Object.gisif_group_index
        del bpy.types.Object.gisif_threshold
        
        del bpy.types.Object.linear_gisif_combinations
        del bpy.types.Object.linear_gisif_n
        
        del bpy.types.Object.gisif_symmetry_index
        del bpy.types.Object.gisif_markers_n
        del bpy.types.Object.gisif_symmetries
        
        
        del bpy.types.Object.live_hks
        del bpy.types.Object.live_wks
        del bpy.types.Object.live_spectral_shape
        del bpy.types.Object.live_gisif
        
        del bpy.types.Object.post_process_colors
        del bpy.types.Object.post_process_min
        del bpy.types.Object.post_process_max
        
        del bpy.types.Object.mean_curvatures_use_normal
        
        del bpy.types.Object.hks_signatures
        del bpy.types.Object.wks_signatures
        del bpy.types.Object.gisif_signatures

        del bpy.types.Object.signatures_dir

def registration_mappings(delete=False):
    if(not delete):
        bpy.types.Object.surfacemappingsbvh = bpy.props.CollectionProperty(type=VertexToSurfaceMappingBVH);
        bpy.types.Object.surfacemappings = bpy.props.CollectionProperty(type=VertexToSurfaceMapping);

        bpy.types.Object.multimappings_entries_count = bpy.props.IntProperty(
        name="MultiMappings Count",
        description="Number of mappings for a mesh",
        default=0
        );
    else:
        del bpy.types.Object.surfacemappingsbvh
        del bpy.types.Object.surfacemappings
        del bpy.types.Object.multimappings_entries_count

def register():
    print('REGISTER PROPERTIES')
    registration_landmarks()
    registration_spectral()
    registration_mappings()


def unregister():
    print('UNREGISTER PROPERTIES')
    registration_landmarks(delete=True)
    registration_spectral(delete=True)
    registration_mappings(delete=True)
    