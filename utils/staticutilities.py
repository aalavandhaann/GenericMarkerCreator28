import bpy, bmesh, mathutils, os;
from mathutils.bvhtree import BVHTree;
import numpy as np;

import platform;

from mathutils import Vector, Color;
# from scipy.interpolate.interpolate_wrapper import logarithmic
from functools import reduce;

from GenericMarkerCreator28.utils.meshmathutils import getKDTree, getBarycentricCoordinate, getBarycentricCoordinateFromPolygonFace;
from GenericMarkerCreator28.utils.mathandmatrices import getBMMesh, ensurelookuptable;


import matplotlib.colors as clrs;
from matplotlib.colors import LinearSegmentedColormap, ListedColormap;


def getConstraintsKD(context, mesh):
    coords = [];
    for m in mesh.generic_landmarks:
        co = Vector((m.location[0], m.location[1], m.location[2]));
        coords.append(co);
    kd = getKDTree(context, mesh, "CUSTOM", coords);
    return kd, coords;

def applyMarkerColor(marker):            
    try:
        material = bpy.data.materials[marker.name+'_MouseMarkerMaterial'];
    except:
        material = bpy.data.materials.new(name=marker.name+'_MouseMarkerMaterial');
    
    material.diffuse_color = (0.0, 0.0, 1.0, 1.0);
    material.specular_color = (0.0, 0.0, 1.0);
    
    marker.data.materials.clear();
    marker.data.materials.append(material);

def detectMorN(mesh):
    M, N = detectMN(mesh);
    
    if(M and N):
#         print(M.name, N.name, mesh.name)
        if(mesh.name == M.name):
#             print('RETURN : ', N.name);
            return N;
#         print('RETURN : ', M.name);
        return M;
    
    return None;

def detectMN(mesh):
    M = None;
    N = None;

    if(not hasattr(mesh, 'generic_landmarks')):
        return M, N
    
    mesh.is_landmarked_mesh = bool(len(mesh.generic_landmarks))

    if(mesh.is_landmarked_mesh):
        M = mesh;
        try:
            N = bpy.data.objects[mesh.mapped_mesh];
        except KeyError:
            print('No paired mesh found, continue with single mesh');
        
    elif(mesh.is_visual_landmark):
        belongsto = bpy.data.objects[mesh.name.split("_marker_")[0]];
        return detectMN(belongsto);
    
    return M, N;

def addConstraint(context, mesh, bary_ratios, bary_indices, co, *, should_reorder=False, faceindex = -1, useid=-1, create_visual_landmarks = True):
    current_ids = [gm.id for gm in mesh.generic_landmarks];
    
    try:
        use_id = int(max(current_ids) + 1);
    except ValueError:
        use_id = mesh.total_landmarks;
        
    if(useid != -1):
        if(useid in current_ids):
            conflicting_id = current_ids[current_ids.index(useid)];
            error_message = 'The given id: %d in argument conflicts with an existing landmark with id: %d.'%(useid, conflicting_id);
            raise ValueError(error_message);
        use_id = useid;
    
    m = mesh.generic_landmarks.add();        
    m.id = use_id;
    m.linked_id = -1;
    m.faceindex = faceindex;
    m.is_linked = False;
    m.v_indices = bary_indices;
    m.v_ratios = bary_ratios;
    m.location = [co.x, co.y, co.z];
    m.landmark_name = 'Original Id: %s'%(m.id);
    
    mesh.total_landmarks = len(mesh.generic_landmarks);
    
    if(should_reorder):
        bpy.ops.genericlandmarks.reorderlandmarks('EXEC_DEFAULT',currentobject=mesh.name);
    else:
        if(create_visual_landmarks):
            tempmarkersource = context.scene.landmarks_use_selection;
            if(tempmarkersource.strip() == ""):
                tempmarkersource = "~PRIMITIVE~";
            bpy.ops.genericlandmarks.createlandmarks('EXEC_DEFAULT',currentobject=mesh.name, markersource=tempmarkersource);
        
    context.view_layer.objects.active =  mesh;
    return m;

def reorderConstraints(context, M, N):
    if(M and N):
        sourcemarkers = [m for m in M.generic_landmarks];
        targetmarkers = [m for m in N.generic_landmarks];
        
        targetmarkerids = [m.id for m in N.generic_landmarks];
        markercouples = [];
        
        nonlinkedsourcemarkers = [m for m in M.generic_landmarks if not m.is_linked];
        nonlinkedtargetmarkers = [m for m in N.generic_landmarks if not m.is_linked];
        
        index = 0;
        
        for sm in sourcemarkers:
            if(sm.is_linked):
                tm = targetmarkers[targetmarkerids.index(sm.linked_id)]; 
                markercouples.append((sm, tm));
        
        for index, (sm, tm) in enumerate(markercouples):
            sm.id = index;
            tm.id = index;
            sm.linked_id = tm.id;
            tm.linked_id = sm.id;
            
        markerindex = index + 1;
        
        for m in nonlinkedsourcemarkers:
            m.id = markerindex;
            markerindex += 1;
            
        M.total_landmarks = markerindex;
        
        markerindex = index + 1;
        
        for m in nonlinkedtargetmarkers:    
            m.id = markerindex;
            markerindex += 1;
        
        N.total_landmarks = markerindex;
    
    else:
        sourcemarkers = [m for m in M.generic_landmarks];
        nonlinkedsourcemarkers = [m for m in M.generic_landmarks if not m.is_linked];
        markerindex = 0;
        for m in nonlinkedsourcemarkers:
            m.id = markerindex;
            markerindex += 1;
            
        M.total_landmarks = markerindex;
    
    
def deleteObjectWithMarkers(context, mesh, onlymarkers=True):
    
    if(context.mode != "OBJECT"):
        bpy.ops.object.mode_set(mode = 'OBJECT', toggle = False);
                        
    if(mesh.is_landmarked_mesh):
        if(mesh.hide_landmarks):
            mesh.hide_landmarks = False;
    
    bpy.ops.object.select_all(action="DESELECT");
    
    context.view_layer.objects.active =  mesh;
    mesh.select_set(True);
    bpy.ops.object.select_grouped(type="CHILDREN_RECURSIVE");
    if(onlymarkers):
        mesh.select_set(False);
    else:
        mesh.select_set(True);
    bpy.ops.object.delete();


def getMarkersForMirrorXByHM(context, mesh, hmarkerslist):
    reflectionmarkers = [];
    belongsto = mesh;
    for hmarker in hmarkerslist:
        reflectionmarker = getMarkerXPlane(belongsto, hmarker);
        if(reflectionmarker):
            reflectionmarkers.append(reflectionmarker);
    
    return reflectionmarkers;
     

def getMarkersForMirrorX(context, bmarkerslist):
    reflectionmarkers = [];
    
    for bmarker in bmarkerslist:
        belongsto = getMeshForBlenderMarker(bmarker);
        hmarker = getGenericLandmark(belongsto, bmarker);
        reflectionmarker = getMarkerXPlane(belongsto, hmarker);
        if(reflectionmarker):
            mirrorbmarker = getBlenderMarker(belongsto, reflectionmarker);
            reflectionmarkers.append(mirrorbmarker);
    
    return reflectionmarkers;

def getMarkerXPlane(meshobject, landmark):
    bl = landmark.location;
    baselocation = Vector((bl[0], bl[1], bl[2]));
    
    hmarkers = [m for m in meshobject.generic_landmarks if m.id != landmark.id];
    
    for m in hmarkers:
        mlocation = Vector((m.location[0], m.location[1], m.location[2]));
        fliplocation = Vector((mlocation.x * -1, mlocation.y, mlocation.z));
        diffDist = (fliplocation - baselocation).length;
        if(diffDist < 0.0001):
            return m;
    return None;

def getGenericLandmark(meshobject, bmarker):
    if(bmarker.is_visual_landmark):
        bnamelist = bmarker.name.split('_marker_');
        originalid = int(bnamelist[1]);
        
        return [m for m in meshobject.generic_landmarks if m.id == originalid][0];
    
    return None;
    
def getBlenderMarker(meshobject, landmark):
    mname = meshobject.name + "_marker_"+str(landmark.id);    
    return bpy.data.objects[mname];

def getMeshForBlenderMarker(blendermarker):
    if(blendermarker.is_visual_landmark):
        if(blendermarker.belongs_to):
            return bpy.data.objects[blendermarker.belongs_to];
        else:
            bnamelist = blendermarker.name.split('_marker_');
            return bpy.data.objects[bnamelist[0]];
    return None
    
def getMarkerOwner(markerobj):
    if(markerobj.is_visual_landmark):
        belongsto = bpy.data.objects[markerobj.name.split("_marker_")[0]];
        return belongsto, False, False;    
    return None, False, False;


def getMarkerType(context, mesh, landmark):
    indices = np.array([vid for vid in landmark.v_indices], dtype=int);
    ratios = np.array([r for r in landmark.v_ratios]);
    c_nz = np.count_nonzero(ratios);
    arg_sorted = np.argsort(ratios)[::-1];
    
    v_indices = None;
    bm = getBMMesh(context, mesh, useeditmode=False);    
    ensurelookuptable(bm);
    if(c_nz == 1):
        v_indices = indices[arg_sorted[[0]]];
        location = bm.verts[v_indices[0]].co.to_tuple();
        bm.free();
        return 'VERTEX', v_indices[0], location, [location];
    elif (c_nz == 2):
        v_indices = indices[arg_sorted[[0, 1]]];
        edges_1 = np.array([e.index for e in bm.verts[v_indices[0]].link_edges]);
        edges_2 = np.array([e.index for e in bm.verts[v_indices[1]].link_edges]);
        edge_common = np.intersect1d(edges_1, edges_2);
        location = tuple([val for val in landmark.location]);
        edge_locations = [bm.verts[v_indices[0]].co.to_tuple(), bm.verts[v_indices[1]].co.to_tuple()];
        bm.free();
        return 'EDGE', edge_common.tolist()[0], location, edge_locations;
    elif(c_nz == 3):
        v_indices = indices[arg_sorted[[0, 1, 2]]];
        faces_1 = np.array([f.index for f in bm.verts[v_indices[0]].link_faces]);
        faces_2 = np.array([f.index for f in bm.verts[v_indices[1]].link_faces]);
        faces_3 = np.array([f.index for f in bm.verts[v_indices[2]].link_faces]);
        face_common = reduce(np.intersect1d, (faces_1, faces_2, faces_3));
        location = tuple([val for val in landmark.location]);
        face_locations = [bm.verts[v_indices[0]].co.to_tuple(), bm.verts[v_indices[1]].co.to_tuple(), bm.verts[v_indices[2]].co.to_tuple()];
        bm.free();
        return 'FACE', face_common.tolist()[0], location, face_locations;
    
    return None, None, None;

def subdivideEdge(bm, edge, point):
        dictio = bmesh.ops.bisect_edges(bm, edges=[edge], cuts=1);
        dictio['geom_split'][0].co = point;
        return dictio['geom_split'][0];

def subdivideFace(bm, face, point):
    retu = bmesh.ops.poke(bm, faces=[face]);
    thevertex = retu['verts'][0];
    thevertex.co = point;
    return thevertex;

def remeshMarkersAsVertices(context, mesh):
    edge_indices = [];
    edge_locations = [];
    
    face_indices = [];
    face_locations = [];
    print('GET ALL LANDMARKS ON EDGE OR FACE');
    for gm in mesh.generic_landmarks:
        gm_on_type, gm_on_type_index, gm_location, gm_locations = getMarkerType(context, mesh, gm);
        if(gm_on_type == 'EDGE'):
            edge_locations.append(gm_location);
            edge_indices.append(gm_on_type_index);
        elif(gm_on_type == 'FACE'):
            face_locations.append(gm_location);
            face_indices.append(gm_on_type_index);
    
    verts_and_locations = [];
    bm = getBMMesh(context, mesh, useeditmode=False);
    print('POKE THE FACES FIRST');
    ensurelookuptable(bm);
    faces = [bm.faces[ind] for ind in face_indices];
    returned_geometry_faces = bmesh.ops.poke(bm, faces=faces);
    
    for i, vert in enumerate(returned_geometry_faces['verts']):
        verts_and_locations.append((vert.index, face_locations[i]));
    
    print('CUT THE EDGES NOW');
    ensurelookuptable(bm);
    edges = [bm.edges[ind] for ind in edge_indices];
    returned_geometry_edges = bmesh.ops.bisect_edges(bm, edges=edges, cuts=1);
    returned_vertices = [vert for vert in returned_geometry_edges['geom_split'] if isinstance(vert, bmesh.types.BMVert)];
        
    for i, vert in enumerate(returned_vertices):
        verts_and_locations.append((vert.index, edge_locations[i]));
            
    ensurelookuptable(bm);
    print('TRIANGULATING THE MESH AS THE LAST STEP FOR MESH');
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0);
    print('NOW MAKE THIS NEW TOPOLOGY TO BE THE MESH');
    bm.to_mesh(mesh.data);
    
    bm.free();
   
    for vid, co in verts_and_locations:
        mesh.data.vertices[vid].co = co;
    print('AUTOCORRECT THE MESH LANDMARKS WITH NEW TOPOLOGY');    
    autoCorrectLandmarksData(context, mesh);
    
def autoCorrectLandmarksData(context, mesh):
    print('AUTOCORRECT: CONSTRUCT KDTREE');
    kd = getKDTree(context, mesh);
    print('AUTOCORRECT: CONSTRUCT BMESH DATA');
    bm = getBMMesh(context, mesh, False);
    print('AUTOCORRECT: CONSTRUCT BMESH DATA ENSURETABLE');
    ensurelookuptable(bm);
    
    print('AUTOCORRECT: ITERATE LANDMARKS AND FIX POSITION');
    for gm in mesh.generic_landmarks:
        loc = [dim for dim in gm.location];
        mco = Vector((loc[0], loc[1], loc[2]));
        
        co, index, dist = kd.find(mco);
        v = bm.verts[index];        
        f = v.link_faces[0];
            
        a = f.loops[0].vert;
        b = f.loops[1].vert;
        c = f.loops[2].vert;        
        u,v,w,ratio,isinside = getBarycentricCoordinate(co, a.co, b.co, c.co);
        gm.v_ratios = [u, v, w];
        gm.v_indices = [a.index, b.index, c.index];
    
    print('AUTOCORRECT: FREE THE BMESH DATA');
    bm.free();
    
def make_colormap(seq):
    """Return a LinearSegmentedColormap
    seq: a sequence of floats and RGB-tuples. The floats should be increasing
    and in the interval (0,1).
    """
    seq = [(None,) * 3, 0.0] + list(seq) + [1.0, (None,) * 3]
    cdict = {'red': [], 'green': [], 'blue': []}
    for i, item in enumerate(seq):
        if isinstance(item, float):
            r1, g1, b1 = seq[i - 1]
            r2, g2, b2 = seq[i + 1]
            cdict['red'].append([item, r1, r2])
            cdict['green'].append([item, g1, g2])
            cdict['blue'].append([item, b1, b2])
    return clrs.LinearSegmentedColormap('CustomMap', cdict);

def getInterpolatedColorValues(error_values, A = None, B = None, *, normalize=True):
    step_colors = [[1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]];
    
    norm = clrs.Normalize(vmin=A, vmax=B);    
    c = clrs.ColorConverter().to_rgb;
    cmap = make_colormap([c('red'), c('yellow'), 0.25, c('yellow'), c('green'), 0.5, c('green'), c('cyan'), 0.75, c('cyan'), c('blue'), 1.0, c('blue') ]);
    c = error_values;
    final_weights = norm(c);

    final_colors = np.zeros((final_weights.shape[0], 4))
    final_colors[:,0:3] = cmap(final_weights)[:, 0:3];
    final_colors[:,-1] = 1.0
    print('COLORS SHAPE ::: ', final_colors.shape)
    if(normalize):
        return final_colors, final_weights;
    return final_colors, error_values;

def applyVertexWeights(context, mesh, weights,*, v_group_name = "lap_errors"):
    if(None == mesh.vertex_groups.get(v_group_name)):
        mesh.vertex_groups.new(name=v_group_name);
    
    group_ind = mesh.vertex_groups[v_group_name].index;
    vertex_group = mesh.vertex_groups[group_ind];
    
    bm = getBMMesh(context, mesh, False);
    ensurelookuptable(bm);
    
    for v in mesh.data.vertices:
        n = v.index;
        vertex_group.add([n], weights[v.index], 'REPLACE');
        b_vert = bm.verts[v.index];               
    bm.free();
    
    return vertex_group;


def applyVertexColors(context, mesh, colors,*, v_group_name = "lap_errors", for_vertices = True):
    if(None == mesh.data.vertex_colors.get(v_group_name)):
        mesh.data.vertex_colors.new(name=v_group_name);
    
    vertex_colors = mesh.data.vertex_colors[v_group_name];
    vertex_colors.active = True;
    try:
        material = bpy.data.materials[mesh.name+'_'+v_group_name];
    except KeyError:
        material = bpy.data.materials.new(name=mesh.name+'_'+v_group_name);
    
    material.use_nodes = True
    node_tree = material.node_tree
    nodes = node_tree.nodes
    nodes.clear()

    principled_bsdf = nodes.get('Vertex Painter') or nodes.new('ShaderNodeBsdfPrincipled')
    vertex_paint_layer = nodes.get('Vertex Paint Layer') or nodes.new('ShaderNodeVertexColor')
    output_layer = nodes.get('Output') or nodes.new('ShaderNodeOutputMaterial')


    vertex_paint_layer.name = 'Vertex Paint Layer'
    principled_bsdf.name = 'Vertex Painter'
    output_layer.name = 'Output'

    vertex_paint_layer.layer_name = vertex_colors.name
    node_tree.links.new(vertex_paint_layer.outputs[0], principled_bsdf.inputs[0])
    node_tree.links.new(principled_bsdf.outputs[0], output_layer.inputs[0])

    
    try:
        mesh.data.materials[mesh.name+'_'+v_group_name];
    except KeyError:
        mesh.data.materials.append(material);
    
    if(for_vertices):
        bm = getBMMesh(context, mesh, False);
        ensurelookuptable(bm);        
        for v in mesh.data.vertices:            
            b_vert = bm.verts[v.index];            
            for l in b_vert.link_loops:
                vertex_colors.data[l.index].color = colors[v.index].r, colors[v.index].g, colors[v.index].b, 1.0;                
        bm.free();
    
    else:        
        for f in mesh.data.polygons:
            for lid in f.loop_indices:
                vertex_colors.data[lid].color = colors[f.index];
    
    return vertex_colors, material;

def getBinEdgeValue(N, hist, edges, fraction):
    sum, partsum = int(N*fraction), 0;
    i = 0;
    for i, h_count in enumerate(hist):
        partsum += h_count;
        if(partsum >= sum):
            break;
    return edges[i+1];

def getMinMax(data, histsize=10000, percent_begin=0.1, percent_end=0.9):
    N = data.shape[0];
    hist, edges = np.histogram(data, bins=histsize);
    min_, max_ = np.min(data), np.max(data);
    threshold = histsize / 5;
    maxcount = np.max(hist);
    if(maxcount > threshold):
#         sorted_data = np.sort(data);
#         newmin = sorted_data[left_index];
#         newmax = sorted_data[right_index];
        
        Nby100 = N / 100;
        left_index = int(Nby100);
        right_index = N - left_index;
        
        
        partition = np.partition(data, left_index) # O(n)    
        newmin = partition[left_index] # O(n)        
        partition = np.partition(data, right_index) # O(n)
        newmax = partition[right_index] # O(n)        
        newmin, newmax = np.min([newmin, newmax]), np.max([newmin, newmax]);        
        hist, edges = np.histogram(data, bins=histsize*50, range=(newmin, newmax));
    
    min_, max_ = getBinEdgeValue(N, hist, edges, percent_begin), getBinEdgeValue(N, hist, edges, percent_end);
    return min_, max_;

def applyColoringForMeshErrors(context, error_mesh, error_values, *, A = None, B = None, v_group_name = "lap_errors", use_weights=False, normalize_weights=True, use_histogram_preprocess=False, percent_min=0.1, percent_max=0.9): 
    if(use_histogram_preprocess):
        min_, max_ = getMinMax(error_values, percent_begin=percent_min, percent_end=percent_max);
#         error_values[np.where(error_values > max_)] = min_;
        error_values = np.clip(error_values, min_, max_);
    
    final_colors, final_weights = getInterpolatedColorValues(error_values, A, B, normalize=normalize_weights);
    
    colors = {};
    weights = {};
    
    iterator_model = [];    
    for_vertices = not (len(error_values) == len(error_mesh.data.polygons));
    
    if(for_vertices):
        iterator_model = error_mesh.data.vertices;
    else:
        iterator_model = error_mesh.data.polygons;
    
    for it_elem in iterator_model:            
        try:
            (r,g,b,a) = final_colors[it_elem.index];
        except ValueError:
            (r,g,b) = final_colors[it_elem.index];            
            a = 1.0
        color = Color((r,g,b));
        colors[it_elem.index] = color;
        weights[it_elem.index] = final_weights[it_elem.index];
    
    if(for_vertices and use_weights):
        applyVertexWeights(context, error_mesh, weights, v_group_name = v_group_name);
    
    applyVertexColors(context, error_mesh, colors, v_group_name=v_group_name, for_vertices=for_vertices);
    

def exportMeshColors(context, mesh, vertex_colors_name, base_location, exportname,*, retain_location=False):
    filepath = os.path.join(base_location, exportname+".ply");
    bpy.ops.object.select_all(action="DESELECT");
    
    mesh.data.vertex_colors.active = mesh.data.vertex_colors[vertex_colors_name];
    context.scene.objects.active = mesh;
    mesh.select = True;    
    o_location = mesh.location.copy();
    if(not retain_location):
        mesh.location = (0,0,0);    
    bpy.ops.export_mesh.ply(filepath=filepath, check_existing=False, axis_forward='-Z', axis_up='Y', filter_glob="*.ply", use_mesh_modifiers=False, use_normals=False, use_uv_coords=False, use_colors=True, global_scale=1.0);
    mesh.location = o_location;
    bpy.ops.object.select_all(action="DESELECT");




     