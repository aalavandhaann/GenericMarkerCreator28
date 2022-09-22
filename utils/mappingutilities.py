import bpy;
import bmesh;

from mathutils import Vector;
from mathutils.bvhtree import BVHTree;

import numpy as np;
import scipy.sparse as spsp;

from GenericMarkerCreator28.utils.staticutilities import getMarkerOwner, getGenericLandmark;
from GenericMarkerCreator28.utils.meshmathutils import getBarycentricCoordinateFromPolygonFace, getGeneralCartesianFromBarycentre;
from GenericMarkerCreator28.utils.mathandmatrices import getDuplicatedObject, getMeshVPos, setMeshVPOS, getWKSLaplacianMatrixCotangent, getColumnFilledMatrix;
from GenericMarkerCreator28.utils.mathandmatrices import getBMMesh, ensurelookuptable;

'''
apply_shape (String) - If not none create a shape key with a name in string value "apply_shape". 
                        Map the deformation of mapping as a shape key to the owner_mesh. If the owner_mesh
                        and apply_on_mesh are the same then this argument has no effect

'''
def deformWithMapping(context, owner_mesh, map_to, apply_on_mesh, mapped_points, use_lse=True, lse_iterations=1, apply_shape=None):
    print('DEFORM WITH MAPPING (UPLIFTING)');
    c = context;        
    constraint_positions = [];
    constraint_ids = [];
    invalid_indices = [];

    depsgraph = context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(map_to, depsgraph)
    ensurelookuptable(bm)
    
    for vid, mapped_point in enumerate(mapped_points):
        if(mapped_point.is_valid):
            co = getGeneralCartesianFromBarycentre(mapped_point.bary_ratios, [map_to.data.vertices[m_vid].co for m_vid in mapped_point.bary_indices]);
            # co = getGeneralCartesianFromBarycentre(mapped_point.bary_ratios, [bm.verts[m_vid].co for m_vid in mapped_point.bary_indices]);
            constraint_ids.append(vid);
            constraint_positions.append(co.to_tuple());
        else:
            invalid_indices.append(vid);
    
    bm.free()
    
    constraint_positions = np.array(constraint_positions, dtype=np.float);
    constraint_ids = np.array(constraint_ids, dtype=np.int);
    invalid_indices = np.array(invalid_indices, dtype=np.int);
    vpos = getMeshVPos(apply_on_mesh);
    print('TOTAL VERTICES : #%s, INVALID INDICES : #%s'%(vpos.shape[0], invalid_indices.shape[0], ));
                
    if(invalid_indices.shape[0] > 0 and invalid_indices.shape[0] != vpos.shape[0] and use_lse):       
        print('SOLVE WITH LSE FOR INVALID MAPPING INDICES');   
        v_group_name='Mapping-LSE-deformer';

        if(None == apply_on_mesh.vertex_groups.get(v_group_name)):
            apply_on_mesh.vertex_groups.new(name=v_group_name);
        
        group_ind = apply_on_mesh.vertex_groups[v_group_name].index;
        vertex_group = apply_on_mesh.vertex_groups[group_ind];    
        vertex_group.remove([v.index for v in apply_on_mesh.data.vertices]);
        apply_on_mesh.modifiers.clear();
        vertex_group.add(constraint_ids.tolist(), 1.0, 'REPLACE');
        
        lap_mod = apply_on_mesh.modifiers.new(name=vertex_group.name, type='LAPLACIANDEFORM');
        lap_mod.vertex_group = vertex_group.name;
        lap_mod.iterations = lse_iterations;#its was 1 before
        
        bpy.ops.object.select_all(action="DESELECT");
        apply_on_mesh.select = True;
        c.scene.objects.active = apply_on_mesh;
        
        bpy.ops.object.laplaciandeform_bind(modifier=lap_mod.name);
        
        bm = getBMMesh(c, apply_on_mesh, useeditmode=False);
        ensurelookuptable(bm);
        for i in range(constraint_ids.shape[0]):
            vid = constraint_ids[i];
            bm.verts[vid].co = constraint_positions[i];
        
        bm.to_mesh(apply_on_mesh.data);
        bm.free();
        bpy.ops.object.modifier_apply(modifier=v_group_name);
    
    elif(invalid_indices.shape[0] == vpos.shape[0]):
        print('NO SOLUTION AVAILABLE FROM THIS MAPPING');
    else:
        print('DIRECT DEFORMATION USING THE MAPPING');
        setMeshVPOS(apply_on_mesh, constraint_positions);

    if(apply_shape and owner_mesh != apply_on_mesh):
        vpos = getMeshVPos(apply_on_mesh)
        shape_keys = owner_mesh.data.shape_keys or owner_mesh.shape_key_add(from_mix=False)
        shape_keys = owner_mesh.data.shape_keys
        shape_key = shape_keys.key_blocks.get(apply_shape) or owner_mesh.shape_key_add(name=apply_shape, from_mix=False)
        shape_key.interpolation = 'KEY_LINEAR'

        for vertex in owner_mesh.data.vertices:
            shape_key.data[vertex.index].co = vpos[vertex.index]

            
    return getMeshVPos(apply_on_mesh), invalid_indices.shape[0];
 