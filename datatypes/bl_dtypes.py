import bpy
import os
import numpy as np

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from GenericMarkerCreator28.utils.mathandmatrices import getBMMesh, ensurelookuptable, getDuplicatedObject
from GenericMarkerCreator28.utils.meshmathutils import getBarycentricCoordinateFromPolygonFace, getCartesianFromBarycentre
from GenericMarkerCreator28.utils.mappingutilities import deformWithMapping

def getMeshBVHTree(context, mesh, deform=True, cage=False):
    depsgraph = context.evaluated_depsgraph_get()
    bvhtree  = BVHTree.FromObject(mesh, depsgraph, deform=deform, cage=cage)    
    return bvhtree


class Point(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty(name = 'index', description="Coordinate index value", default=-1);
    x: bpy.props.FloatProperty(name = 'x', description="Coordinate X value", default=0.00);
    y: bpy.props.FloatProperty(name = 'y', description="Coordinate Y value", default=0.00);
    z: bpy.props.FloatProperty(name = 'z', description="Coordinate Z value", default=0.00);
    w: bpy.props.FloatProperty(name = 'w', description="Coordinate W value", default=0.00);

class GenericLandmark(bpy.types.PropertyGroup):
    is_linked: bpy.props.BoolProperty(name="Is Linked", description="Flag to check if a landmark is linked", default=False);
    id: bpy.props.IntProperty(name="Landmark Id", description="Index or indentifier that is unique for this landmark", default=-1);
    linked_id: bpy.props.IntProperty(name="Linked Constraint Id", description="Index or indentifier of the unique indexed constraint to which this landmark is mapped.", default=-1);    
    faceindex: bpy.props.IntProperty(name="Triangle Index", description="Index or indentifier of the triangle on which this landmark is placed.", default=-1);
    v_indices: bpy.props.IntVectorProperty(name="Vertex indices", description="Vertex indices on which the barycentric ratios have to be applied",default=(-1, -1, -1));
    v_ratios: bpy.props.FloatVectorProperty(name="Barycentric ratios", description="Given the vertex indices (==3) apply the barycentric ratios for the location of the marker",default=(0.0,0.0,0.0));
    location: bpy.props.FloatVectorProperty(name="Location of Landmark",default=(0.0,0.0,0.0));
    landmark_name: bpy.props.StringProperty(name="Landmark Name", default="No Name");
    
    def updateLocation(self):
        owner_mesh = self.id_data
        
        polygons = owner_mesh.data.polygons
        loops = owner_mesh.data.loops
        vertices = owner_mesh.data.vertices

        face = polygons[self.faceindex]        
        a, b, c = [vertices[loops[lid].vertex_index].co for lid in face.loop_indices]

        ba = Vector(self.v_ratios)
        coord = getCartesianFromBarycentre(ba, a, b, c)
        self.location = coord.xyz

    def bestVertex(self):
        v_indices = [i for i in self.v_indices]
        v_ratios = [r for r in self.v_ratios]
        max_ratio_index = np.argmax(v_ratios)
        return v_indices[max_ratio_index], v_ratios[max_ratio_index]

    def bestVertexRatio(self):
        _, ratio = self.bestVertex()
        return ratio

    def bestVertexIndex(self):
        vid, _ = self.bestVertex()
        return vid

    def copyToLandmark(self, landmark):
        landmark.id = self.id;
#         landmark.is_linked = self.is_linked;
#         landmark.linked_id = self.linked_id;
        landmark.faceindex = self.faceindex;
        landmark.v_indices = self.v_indices;
        landmark.v_ratios = self.v_ratios;
        landmark.location = self.location;
        landmark.landmark_name = self.landmark_name;
    
    def copyFromLandmark(self, landmark):
        self.id = landmark.id;
#         self.is_linked = landmark.is_linked;
#         self.linked_id = landmark.linked_id;
        self.faceindex = landmark.faceindex;
        self.v_indices = landmark.v_indices;
        self.v_ratios = landmark.v_ratios;
        self.location = landmark.location;
        self.landmark_name = landmark.landmark_name;


class GenericPointSignature(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty(name="Index", description="Index or indentifier that is unique for this landmark", default=-1);
    name: bpy.props.StringProperty(name="Signature Name", default="");
    
    gisif: bpy.props.FloatProperty(name = 'GISIF', description="The signature for this point", default=0.00);    
    k1: bpy.props.FloatProperty(name = 'k1', description="The k1 signature for this point", default=0.00);
    k2: bpy.props.FloatProperty(name = 'k2', description="The k2 signature for this point", default=0.00);
    
    normal: bpy.props.FloatVectorProperty(name = 'Curvature Normal', description="The normal signature for this point", default=(0.0, 0.0, 0.0));
    p1: bpy.props.FloatVectorProperty(name = 'Principal Direction 1', description="The p1 signature for this point", default=(0.0, 0.0, 0.0));
    p2: bpy.props.FloatVectorProperty(name = 'Principal Direction 2', description="The p2 signature for this point", default=(0.0, 0.0, 0.0));

class VertexMapping(bpy.types.PropertyGroup):
    face_index: bpy.props.IntProperty(name="Face Index", description="Triangle Index of the mapped location",default=-1);
    bary_indices: bpy.props.IntVectorProperty(name="Vertex indices", description="Vertex indices on which the barycentric ratios have to be applied",default=(-1, -1, -1));
    bary_ratios: bpy.props.FloatVectorProperty(name="Barycentric ratios", description="Given the vertex indices (==3) apply the barycentric ratios for the location of mapped point",default=(0.0,0.0,0.0));
    is_valid: bpy.props.BoolProperty(name="Is Valid?", description="Is this a valid mapping point", default=True);
    
class VertexToSurfaceMappingBVH(bpy.types.PropertyGroup):
    mapping_name: bpy.props.StringProperty(name='Map Name', description="Maping Name", default='Mapping');
    map_to_mesh: bpy.props.StringProperty(name='Map To', description="Map to Mesh surface name", default='--');
    export_file_path: bpy.props.StringProperty(name="Export Mapping File", description="Location of the mapping file", subtype='FILE_PATH', default='mapping.map');

    mapped_points: bpy.props.CollectionProperty(type=VertexMapping);
    filter_angle_value: bpy.props.FloatProperty(name='Filter Angle', description='Dot value to consider', default=0.95);
    num_lse_iterations: bpy.props.IntProperty(name='LSE Iterations', description='Total LSE Iterations', default=1);
    
    apply_on_duplicate: bpy.props.BoolProperty(name="Apply Duplicate", description="Apply the mapping to deform on duplicate", default=True);
    apply_as_shape: bpy.props.BoolProperty(name="Apply as Shape", description="Apply the mapping deformation as shape key", default=False);
    use_lse_iterations: bpy.props.BoolProperty(name='Use LSE Iterations', description='Should Use LSE Iterations', default=True);
    
    def constructMapping(self):
        c = bpy.context;
        owner_mesh = self.id_data;
#         if(not createmapping):
#             return;
        try:
            map_to = c.scene.objects[self.map_to_mesh];

            # mat1 = map_to.matrix_world
            # vert1 = [mat1 @ v.co for v in map_to.data.vertices] 
            # poly1 = [p.vertices for p in map_to.data.polygons]
            btree = getMeshBVHTree(c, map_to)#.FromPolygons( vert1, poly1 )

            n_count = len(owner_mesh.data.vertices);
            self.mapped_points.clear();
            for vid, v in enumerate(owner_mesh.data.vertices):
                mapped_point = self.mapped_points.add();
                x, y, z = v.co.to_tuple();
                co, n, i, d = btree.find_nearest(Vector((x,y,z)));
                #Also check if the normals deviation is < 45 degrees
#                 if(co and n and i and d and (n.normalized().dot(v.normal.normalized()) > 0.75)):
                if(co and n):
                    face = map_to.data.polygons[i];
                    if((face.normal.normalized().dot(v.normal.normalized()) > self.filter_angle_value)):
                        u,v,w,ratio, isinside, vid1, vid2, vid3 = getBarycentricCoordinateFromPolygonFace(co, face, map_to, snapping=False, extra_info = True);
                        mapped_point.face_index = i;
                        mapped_point.bary_ratios = [u, v, w];
                        mapped_point.bary_indices = [vid1, vid2, vid3];
                    else:
                        mapped_point.is_valid = False;
                else:
                    mapped_point.is_valid = False
        except KeyError:
            print('MAP TO MESH NEEDS TO BE SET BEFORE CONSTRUCTING A MAPPING');
            raise;
        
    def deformWithMapping(self):
        print('DEFORM WITH MAPPING (UPLIFTING)');
        c = bpy.context;
        owner_mesh = self.id_data;
        apply_on_name = "%s-%s-%s"%(owner_mesh.name, self.mapping_name, self.name)
        try:
            map_to = c.scene.objects[self.map_to_mesh];
            apply_on_mesh = owner_mesh;            

            try:
                apply_on_mesh = c.scene.objects[apply_on_name];
            except KeyError:
                apply_on_mesh = getDuplicatedObject(c, owner_mesh, meshname=apply_on_name);

            apply_shape = None
            if(self.apply_as_shape):
                apply_shape = apply_on_name

            mapped_positions, count_invalid = deformWithMapping(c, owner_mesh, map_to, apply_on_mesh, self.mapped_points, self.use_lse_iterations, self.num_lse_iterations, apply_shape=apply_shape);                                
            
            #If apply on duplicate is false then do not retain the duplicated object and delete it
            if(not self.apply_on_duplicate):
                bpy.ops.object.select_all(action='DESELECT')
                c.view_layer.objects.active = apply_on_mesh
                apply_on_mesh.select_set(True)
                bpy.ops.object.delete()

                c.view_layer.objects.active = owner_mesh
                owner_mesh.select_set(True)
                apply_on_mesh = owner_mesh

            
            return apply_on_mesh, mapped_positions, count_invalid;
        
        except KeyError:
            print('MAP TO MESH NEEDS TO BE SET BEFORE CONSTRUCTING A MAPPING');
            raise;        
        
    def copyMappingToMesh(self, to_mesh):
        from_mesh = self.id_data;
        try:
            assert (len(from_mesh.data.vertices) == len(to_mesh.data.vertices));
        except AssertionError:
            print(('Meshes %s and %s should have same connectivity'%(from_mesh.name, to_mesh.name)).upper());
            raise;
        
        mapping = to_mesh.surfacemappingsbvh.add();
        mapping.name = self.name;
        mapping.map_to_mesh = self.map_to_mesh;
        mapping.mapped_points.clear();
        for mapped_point in self.mapped_points:
            mpoint = mapping.mapped_points.add();
            mpoint.is_valid = mapped_point.is_valid;
            if(mpoint.is_valid):
                mpoint.face_index = mapped_point.face_index;
                mpoint.bary_indices = [id for id in mapped_point.bary_indices];
                mpoint.bary_ratios = [r for r in mapped_point.bary_ratios]; 
        
        return mapping;
    
    def exportMapping(self):
        export_mapping_file_path = bpy.path.abspath(self.export_file_path);
        owner_mesh = self.id_data;
        entries = [];
        for vid, mapped_point in enumerate(self.mapped_points):
            if(mapped_point.is_valid):
                u,v,w = mapped_point.bary_ratios;
                vid1,vid2,vid3 = mapped_point.bary_indices;
                entries.append([vid1,vid2,vid3,u,v,w]);
            else:
                entries.append([-1,-1,-1,0.0,0.0,0.0]);
        
        entries = np.array(entries);   
        np.savetxt(export_mapping_file_path, entries);

class VertexToSurfaceMapping(bpy.types.PropertyGroup):
    mapping_name: bpy.props.StringProperty(name='Map Name', description="Maping Name", default='Mapping');
    map_to_mesh: bpy.props.StringProperty(name='Map To', description="Map to Mesh surface name", default='--');
    file_path: bpy.props.StringProperty(name="Mapping File", description="Location of the mapping file", subtype='FILE_PATH', default='mapping.map');
    export_file_path: bpy.props.StringProperty(name="Export Mapping File", description="Location of the mapping file", subtype='FILE_PATH', default='mapping.map');
    
    apply_on_duplicate: bpy.props.BoolProperty(name="Apply Duplicate", description="Apply the mapping to deform on duplicate", default=True);
    apply_as_shape: bpy.props.BoolProperty(name="Apply as Shape", description="Apply the mapping deformation as shape key", default=False);
    mapping_is_valid: bpy.props.BoolProperty(name="Mapping Valid", description="Is the Mapping Valid?", default=False);
    use_lse_iterations: bpy.props.BoolProperty(name='Use LSE Iterations', description='Should Use LSE Iterations', default=True);
    
    num_lse_iterations: bpy.props.IntProperty(name='LSE Iterations', description='Total LSE Iterations', default=1);
    mapped_points: bpy.props.CollectionProperty(type=VertexMapping);
    
    def constructFromFile(self, mapping_file_path, owner_mesh, map_to):
        n_count = len(owner_mesh.data.vertices);
        self.mapped_points.clear();
        
#         np_file = np.loadtxt(mapping_file_path, dtype={'names':['index','u','v','w'], 'formats':[int, float, float, float]});
#         np_file = np.loadtxt(mapping_file_path, dtype={'names':['index','u','v','w'], 'formats':[int, float, float, float]});
        try:
            np_file = np.loadtxt(mapping_file_path, dtype=None);
        except ValueError:
            np_file = np.loadtxt(mapping_file_path, dtype=None,delimiter=",",);
        isTriangleMapped = False;
        isVertexMapped = False;
        isVertexToVertexMapped = False;
        
        try:
            isTriangleMapped = (np_file.shape[1] == 4);
            isVertexMapped =  (np_file.shape[1] == 6);
        except IndexError:
            isVertexToVertexMapped = True;
            ids = np_file;
            bm = getBMMesh(bpy.context, map_to, useeditmode=False);
            ensurelookuptable(bm);
        
        if(isTriangleMapped):
            ids = np_file[:,0].astype(int);
            ratios = np_file[:,-3:].astype(float);
        elif(isVertexMapped):
            ids = np_file[:,:3].astype('int');
            ratios = np_file[:,-3:].astype(float);
        
        print(ids.shape, ids[0]);
        loops = map_to.data.loops;
        vertices = map_to.data.vertices;
        
        for vid, v in enumerate(owner_mesh.data.vertices):
            mapped_point = self.mapped_points.add();            
            if(isTriangleMapped):
                fid = ids[vid];
                u, v, w = ratios[vid];
                if(fid == -1):
                    mapped_point.is_valid = False;
                else:
                    face = map_to.data.polygons[fid];
                    vids = [loops[lid].vertex_index for lid in face.loop_indices];
                    vid1, vid2, vid3 = vids;                
            elif(isVertexMapped):
                vid1, vid2, vid3 = [int(ii) for ii in ids[vid]];
                u, v, w = ratios[vid];
                if(vid1 == -1 and vid2 == -1 and vid3 == -1):
                    mapped_point.is_valid = False;
                    
            elif(isVertexToVertexMapped):
                useVertexTargetId = int(ids[vid]);
                if(useVertexTargetId != -1):
                    bmface = bm.verts[useVertexTargetId].link_faces[0];
                    t_verts = [l.vert.index for l in bmface.loops];
                    t_ratios = [0.0, 0.0, 0.0];
                    t_ratios[t_verts.index(useVertexTargetId)] = 1.0;
                    vid1, vid2, vid3 = t_verts;
                    u, v, w = t_ratios;
                else:
                    mapped_point.is_valid = False;
            if(mapped_point.is_valid):
                mapped_point.bary_ratios = [u, v, w];
                mapped_point.bary_indices = [vid1, vid2, vid3];
        
        self.mapping_is_valid = True;
        try:
            bm.free();
        except NameError:
            pass;
        
        return True;
    
    def constructMappingBVH(self, owner_mesh, map_to):
        c = bpy.context;

        # mat1 = map_to.matrix_world
        # vert1 = [mat1 @ v.co for v in map_to.data.vertices] 
        # poly1 = [p.vertices for p in map_to.data.polygons]
        # btree = BVHTree.FromPolygons( vert1, poly1 )
        btree = getMeshBVHTree(c, map_to)

        n_count = len(owner_mesh.data.vertices);
        self.mapped_points.clear();
        for vid, v in enumerate(owner_mesh.data.vertices):
            mapped_point = self.mapped_points.add();
            x, y, z = v.co.to_tuple();
            co, n, i, d = btree.find_nearest(Vector((x,y,z)));
            if(co and n):
                face = map_to.data.polygons[i];
                u,v,w,ratio, isinside, vid1, vid2, vid3 = getBarycentricCoordinateFromPolygonFace(co, face, map_to, snapping=False, extra_info = True);
                mapped_point.face_index = i;
                mapped_point.bary_ratios = [u, v, w];
                mapped_point.bary_indices = [vid1, vid2, vid3];
            else:
                mapped_point.is_valid = False;
        
        self.mapping_is_valid = True;
        return True;
    
    def constructMapping(self):
        c = bpy.context;
        mapping_file_path = bpy.path.abspath(self.file_path);
        try:
            owner_mesh = self.id_data;
            map_to = c.scene.objects[self.map_to_mesh];        
        except KeyError:
            print('MAP TO MESH NEEDS TO BE SET BEFORE CONSTRUCTING A MAPPING');
            raise KeyError;
        
        if(os.path.exists(mapping_file_path)):
            return self.constructFromFile(mapping_file_path, owner_mesh, map_to);
        else:
            print('USE BVH TO CONSTRUCT THE MAPPING BECAUSE THE MAPPING FILE DOES ');
            return self.constructMappingBVH(owner_mesh, map_to);
            
        return False;
    
    def exportMapping(self):
        export_mapping_file_path = bpy.path.abspath(self.export_file_path);
        owner_mesh = self.id_data;
        entries = [];
        for vid, mapped_point in enumerate(self.mapped_points):
            if(mapped_point.is_valid):
                u,v,w = mapped_point.bary_ratios;
                vid1,vid2,vid3 = mapped_point.bary_indices;
                entries.append([vid1,vid2,vid3,u,v,w]);
            else:
                entries.append([0,0,0,0.0,0.0,0.0]);        
        
        entries = np.array(entries);   
        np.savetxt(export_mapping_file_path, entries);
        
        
    def deformWithMapping(self):
        print('DEFORM WITH MAPPING (UPLIFTING)');
        c = bpy.context;
        owner_mesh = self.id_data;
        apply_on_name = "%s-%s-%s"%(owner_mesh.name, self.mapping_name, self.name)
        try:
            map_to = c.scene.objects[self.map_to_mesh];
            apply_on_mesh = owner_mesh;            

            try:
                apply_on_mesh = c.scene.objects[apply_on_name];
            except KeyError:
                apply_on_mesh = getDuplicatedObject(c, owner_mesh, meshname=apply_on_name);

            apply_shape = None
            if(self.apply_as_shape):
                apply_shape = apply_on_name

            mapped_positions, count_invalid = deformWithMapping(c, owner_mesh, map_to, apply_on_mesh, self.mapped_points, self.use_lse_iterations, self.num_lse_iterations, apply_shape=apply_shape);                                
            
            #If apply on duplicate is false then do not retain the duplicated object and delete it
            if(not self.apply_on_duplicate):
                bpy.ops.object.select_all(action='DESELECT')
                c.view_layer.objects.active = apply_on_mesh
                apply_on_mesh.select_set(True)
                bpy.ops.object.delete()

                c.view_layer.objects.active = owner_mesh
                owner_mesh.select_set(True)
                apply_on_mesh = owner_mesh

            
            return apply_on_mesh, mapped_positions, count_invalid;
        
        except KeyError:
            print('MAP TO MESH NEEDS TO BE SET BEFORE CONSTRUCTING A MAPPING');
            raise;          
        
    def copyMappingToMesh(self, to_mesh):        
        from_mesh = self.id_data;
        try:
            assert (len(from_mesh.data.vertices) == len(to_mesh.data.vertices));
        except AssertionError:
            print(('Meshes %s and %s should have same connectivity'%(from_mesh.name, to_mesh.name)).upper());
            raise;
        
        mapping = to_mesh.surfacemappingsbvh.add();
        mapping.name = self.name;
        mapping.map_to_mesh = self.map_to_mesh;
        mapping.mapped_points.clear();
        for mapped_point in self.mapped_points:
            mpoint = mapping.mapped_points.add();
            mpoint.is_valid = mapped_point.is_valid;
            if(mpoint.is_valid):
                mpoint.face_index = mapped_point.face_index;
                mpoint.bary_indices = [id for id in mapped_point.bary_indices];
                mpoint.bary_ratios = [r for r in mapped_point.bary_ratios]; 
        
        return mapping;