import bpy
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils.bvhtree import BVHTree;

import numpy as np;
import scipy.sparse as spsp;
from scipy.sparse import csr_matrix, lil_matrix;
from scipy.sparse.csgraph import minimum_spanning_tree;

from GenericMarkerCreator28.utils.interactiveutilities import ScreenPoint3D;
from GenericMarkerCreator28.utils.bgl_utilities import getPointBatch, getHollowCircleBatch, getPathBatch, getPathAsBatchesWithPoints, getPathAsBatchesWithLines
from GenericMarkerCreator28.utils.mathandmatrices import buildKDTree, getBMMesh, ensurelookuptable
from GenericMarkerCreator28.utils.staticutilities import detectMN

from GenericMarkerCreator28.geodesics.geodesicgraphpaths import ChenhanGeodesics, isFastAlgorithmLoaded;

class GeodesicCutterWithLandmarks(bpy.types.Operator):
    bl_idname = "genericlandmarks.geodesic_cutter_landmarks";
    bl_label = "Landmark Seams";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_description = "Generating cuts on mesh surfaces connecting landmarks and using geodesic paths"

    snap_landmarks: bpy.props.StringProperty(name="Snap Landmarks", default="Snap landmarks to closest vertices?")
    confirmation: bpy.props.EnumProperty(
        name="Confirm",
        items= [
            ('yes',"Yes",''),
            ('no',"No",''),
        ],
    )
    show_seams: bpy.props.BoolProperty(name="Show Landmark Seams", description="If you have to show seams then use modal operator to show the seam paths", default=False)

    def getGeodesicAlgorithm(self, context, mesh):
        bm = getBMMesh(context, mesh, False)
        richmodel = None

        if(not isFastAlgorithmLoaded):
            richmodel = RichModel(bm, mesh)
            richmodel.Preprocess()
        
        chenhan = ChenhanGeodesics(context, mesh, bm, richmodel)        
        return chenhan, bm

    def getGeodesicMatrixGraph(self, context, mesh):
        seed_indices = [gm.bestVertexIndex() for gm in mesh.generic_landmarks]
        algorithm, bm = self.getGeodesicAlgorithm(context, mesh)
        K = len(seed_indices)
        np_matrix = np.zeros((K, K))

        wm = context.window_manager
        wm.progress_begin(0, len(seed_indices))
        for i,vid in enumerate(seed_indices):
            algorithm.addSeedIndex(vid)
            v_distances = algorithm.getVertexDistances(vid);
            np_matrix[i] = np.array(v_distances)[seed_indices];
            wm.progress_update(i+1)

        wm.progress_end()
        bm.free()
        return csr_matrix(np_matrix), algorithm

    def getSpanningGraphAndGeodesicAlgorithm(self, context, mesh):
        spanning_graph, geodesic_alg = self.getGeodesicMatrixGraph(context, mesh)
        return geodesic_alg, spanning_graph


    def getLandmarksConnectivity(self, context, M, N):
        geodesc_alg_M, spanning_graph_M = self.getSpanningGraphAndGeodesicAlgorithm(context, M)
        geodesc_alg_N, spanning_graph_N = None, np.zeros(spanning_graph_M.shape)
        if(N):
            geodesc_alg_N, spanning_graph_N = self.getSpanningGraphAndGeodesicAlgorithm(context, N)

        spanning_graph = spanning_graph_M + spanning_graph_N
        spanningtree = minimum_spanning_tree(spanning_graph, overwrite=False)
        #         plotting Minimum spanning tree
        coo = spanningtree.tocoo()
        edges = zip(coo.row, coo.col)
        edges = sorted(tuple(sorted(pair)) for pair in edges)

        return edges, geodesc_alg_M, geodesc_alg_N
    
    def createSeamsBreakingEdges(self, context, mesh, paths):
        mesh_data = mesh.data
        matrix = mesh.matrix_world

        vertices = mesh_data.vertices
        '''
            Create fake triangles from edges using the two vertices of the edge 
            as (edge.vertices[0], edge.vertices[1], edge.vertices[0])
        '''
        polygons = [(e.vertices[0], e.vertices[1], e.vertices[0]) for e in mesh_data.edges]
        tree = BVHTree.FromPolygons(vertices, polygons, all_triangles = True)

        break_the_edges = []

    def getCurvesForGeodesicPath(self, context, mesh, geodesic_algorithm, gm_from, gm_to):
        gm_from_id, gm_to_id = gm_from.id, gm_to.id
        vid1, vid2 = gm_from.v_indices[np.argmax(gm_from.v_ratios)], gm_to.v_indices[np.argmax(gm_to.v_ratios)]
        
        geodesic_path = geodesic_algorithm.path_between(vid1, vid2, local_path=False)
        
        curve_name = '%s-path-%s-%s'%(mesh.name, gm_from_id, gm_to_id)
        curve = bpy.data.curve.new(curve_name, type='CURVE')
        curve_object = bpy.data.objects.new(curve_name, curve)
        
        
        curve_points = curve.splines.new('POLY')
        curve_points.points.add(len(geodesic_path))

        for i,geo_point in enumerate(geodesic_path):
            x,y,z = geo_point.xyz
            curve_points.points[i].co = (x, y, z, 1)       

        
        curve.dimensions = '3D'
        curve.resolution_u = 0.01
        curve.bevel_depth = 0.01
        
        context.scene.collection.objects.link(curve_object)
        return curve_object, curve

    def getSeamCurvesForMesh(self, context, mesh, connectivity):
        for marker_id_1, marker_id_2 in connectivity:
            gm_from, gm_to = mesh.generic_landmarks[marker_id_1], mesh.generic_landmarks[marker_id_2]


    def getCurvesDistributionForMandN(self, context, M, N):
        connectivity, geodesc_alg_M, geodesc_alg_N = self.getLandmarksConnectivity(context, M, N)
        

        return None, None

    def execute(self, context):
        if(not context.active_object):
            self.report({'ERROR'}, 'Select a mesh object and make it active')
            return {'CANCELLED'}
        if(context.active_object and context.active_object.type != 'MESH'):
            self.report({'ERROR'}, 'Works only with meshes')
            return {'CANCELLED'}

        if(not isFastAlgorithmLoaded()):
            self.report({'ERROR'}, 'You need py_chenhancc for this operator to work. Install using pip install py_chenhancc')
            return {'CANCELLED'}

        
        print('CONFIRMATION :::', self.confirmation)
        if(self.confirmation == 'yes'):        
            M, N = detectMN(context.active_object);
            print('M & N ', M, N)

            if(not M):
                self.report({'ERROR'}, 'Works only on meshes with landmarks')
                return {'CANCELLED'}

            if(len(context.active_object.generic_landmarks) < 2):
                self.report({'ERROR'}, 'Use a mesh with more than one landmark')
                return {'CANCELLED'}
            bpy.ops.genericlandmarks.reorderlandmarks('EXEC_DEFAULT', currentobject=M.name)
            bpy.ops.genericlandmarks.snaplandmarkstovertex('EXEC_DEFAULT', currentobject=M.name, create_vertices=M.snap_landmarks_create_vertices, apply_on_duplicate=M.snap_landmarks_apply_on_duplicate)
            curves_M, curves_N = self.getCurvesDistributionForMandN(context, M, N)

        else:
            self.report({'WARNING'}, 'Landmarks based seams not applied')   
            return {'CANCELLED'}

        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def draw(self, context):
        box = self.layout.box()
        box.label(text='User Action Required')
        row = box.row()
        row.label(text=self.snap_landmarks)
        row = box.row()
        row.prop(self, "confirmation", expand=True)

    def invoke(self, context, event):
        confirm = context.window_manager.invoke_props_dialog(self, width=400)        
        return confirm


#The operators for creating landmarks
class GeodesicPaths(bpy.types.Operator):
    bl_idname = "genericlandmarks.geodesic_paths";
    bl_label = "Geodesic Paths";
    bl_space_type = "VIEW_3D";
    bl_region_type = "UI";
    bl_context = "objectmode";
    bl_description = "Show geodesic paths between successive clicks on a mesh surface"

    def modal(self, context, event):
        if event.type in {'ESC'}:
            context.area.header_text_set(text="");
            bpy.ops.object.select_all(action="DESELECT");
            self.mousepointer.hide_select = False
            self.mousepointer.hide_viewport = False
            self.mousepointer.select_set(True);
            context.view_layer.objects.active = self.mousepointer;
            bpy.ops.object.delete();
            self.__finish(context)
            return {'CANCELLED'}
        if(event.type in {'MOUSEMOVE'}):
            hit, onM, m_face_index, m_hitpoint = ScreenPoint3D(context, event, position_mouse = False, use_mesh=self.M);
            if(m_hitpoint):
                self.__mouse_cursor_batch = getPointBatch(context, self.shader, self.M.matrix_world @ m_hitpoint, color= (0, 0, 1, 1))
                context.area.header_text_set("Mouse: (%.8f %.8f %.8f)" % (m_hitpoint.x, m_hitpoint.y, m_hitpoint.z));
                self.mousepointer.location = m_hitpoint;
                _, v_i, _ = self.kdtree_m.find(m_hitpoint)
                currentseed = v_i

                if(len(self.chenhan.getSeedIndices()) > 0): 
                    p_indices = self.chenhan.getSeedIndices()
                    temp_paths = self.__get_sequenced_shortest_path(p_indices[-1], currentseed)
                    if(temp_paths):
                        if(len(temp_paths)):
                            points_batch = getPathAsBatchesWithPoints(context, self.shader, temp_paths, color=(0.0, 0.25, 0.25, 1), pointsize=10)
                            lines_batch = getPathAsBatchesWithLines(context, self.shader, temp_paths, color=(0.0, 0.25, 0.25, 1))
                            self.__temp_path_batches = [points_batch]
                            self.__temp_path_batches.append(lines_batch)

        if (event.type in {'LEFTMOUSE'}):
            hit, onM, m_face_index, m_hitpoint = ScreenPoint3D(context, event, position_mouse = False, use_mesh=self.M);
            if(m_hitpoint):
                _, v_i, d_i = self.kdtree_m.find(m_hitpoint)
                self.__add_vertex_indice(context, v_i)
                self.__temp_path_batches = None
                return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if(not context.active_object):
            self.report({'ERROR'}, 'Select a mesh object and make it active')
            return {'CANCELLED'}
        if(context.active_object and context.active_object.type != 'MESH'):
            self.report({'ERROR'}, 'Works only with meshes')
            return {'CANCELLED'}

        if(not isFastAlgorithmLoaded()):
            self.report({'ERROR'}, 'You need py_chenhancc for this operator to work. Install using pip install py_chenhancc')
            return {'CANCELLED'}
        
        self.M = context.active_object
        self.marker_ring_size = max(self.M.dimensions) * 0.01;
        self.mesh_show_wire = self.M.show_wire
        self.mesh_show_all_edges = self.M.show_all_edges

        self.M.show_all_edges = True
        self.M.show_wire = True

        maxsize = max(self.M.dimensions.x, self.M.dimensions.y, self.M.dimensions.z);
        markersize = maxsize * 0.01;            
        tempmarkersource = "Marker";
        
        try:
            tempmarker = bpy.data.objects[tempmarkersource];
        except KeyError:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=36, ring_count = 36);
            tempmarker = context.object;
            tempmarker.name = "Marker";

        tempmarker.dimensions = (markersize,markersize,markersize);
        tempmarker.hide_select = True
        tempmarker.hide_viewport = True
        self.mousepointer = tempmarker;


        # Get their world matrix
        mat1 = self.M.matrix_world
        # Get the geometry in world coordinates
        vert1 = [mat1 @ v.co for v in self.M.data.vertices] 
        poly1 = [p.vertices for p in self.M.data.polygons]
        self.bvhtree_m = BVHTree.FromPolygons( vert1, poly1 )
        self.kdtree_m = buildKDTree(context, self.M)

        self.bm = getBMMesh(context, self.M, False);
        self.richmodel = None;

        if(not isFastAlgorithmLoaded):
            self.richmodel = RichModel(self.bm, self.M);
            self.richmodel.Preprocess();
        
        self.chenhan = ChenhanGeodesics(context, self.M, self.bm, self.richmodel);
        self.currentseed = 0;
        
        if(isFastAlgorithmLoaded()):
            self.richmodel = self.chenhan.getRichModel();

        
        self.__geo_vertex_indices = []

        self.__geodesic_paths = []
        self.__drawbatches = []
        self.__create_shader(context)


        args = (self, context)
        self.__register_handlers(args, context)
        context.window.cursor_modal_set('KNIFE')
        context.window_manager.modal_handler_add(self)
        # bpy.ops.object.mode_set(mode='EDIT')
        return {'RUNNING_MODAL'}
    

    def __get_sequenced_shortest_path(self, v1, v2,*, local_path = False):
        path = None;
        if(v1 != v2):
            path = self.chenhan.path_between(v1, v2, local_path = local_path);
        return path

    def __add_vertex_indice(self, context, vid):
        if(vid not in self.__geo_vertex_indices):
            self.__geo_vertex_indices.append(vid)

            if(vid not in self.chenhan.getSeedIndices()):
                context.window.cursor_modal_set('WAIT')
                self.chenhan.addSeedIndex(vid);
                context.window.cursor_modal_set('KNIFE')
                self.currentseed = vid;

            del self.__drawbatches[:]
            del self.__geodesic_paths[:]

            for i, vid in enumerate(self.__geo_vertex_indices):
                co = self.M.matrix_world @ self.M.data.vertices[vid].co
                point_batch = getPointBatch(context, self.shader, co)
                hollow_circle_batch = getHollowCircleBatch(context, self.shader, co, self.M.data.vertices[vid].normal, radius=self.marker_ring_size)
                
                if(i > 0):
                    seed_index = self.__geo_vertex_indices[i-1]
                    target_index = vid
                    context.window.cursor_modal_set('WAIT')
                    path_between = self.__get_sequenced_shortest_path(seed_index, target_index)
                    context.window.cursor_modal_set('KNIFE')
                    
                    if(path_between):
                        if(len(path_between)):
                            path_batch_points = getPathAsBatchesWithPoints(context, self.shader, path_between, pointsize=10)
                            path_batch_lines = getPathAsBatchesWithLines(context, self.shader, path_between)
                            self.__geodesic_paths.extend(path_between)
                            self.__drawbatches.append(path_batch_points)
                            self.__drawbatches.append(path_batch_lines)

                self.__drawbatches.append(point_batch)
                self.__drawbatches.append(hollow_circle_batch)


    
    def __finish(self, context):
        # context.window.cursor_modal_set('DEFAULT')        
        context.window.cursor_modal_restore()
        self.__unregister_handlers(context)
        self.M.show_all_edges = self.mesh_show_all_edges
        self.M.show_wire = self.mesh_show_wire
        
        return {'FINISHED'}
    
    def __create_shader(self, context):
        '''
            https://docs.blender.org/api/current/gpu.shader.html?highlight=from_builtin#gpu.shader.from_builtin
            for different builtin drawing methods
            essentially you created different shaders to draw different types of drawings
        '''
        self.shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        self.__mouse_cursor_batch = getPointBatch(context, self.shader, (0, 0, 0), color= (0, 0, 1, 1)) 
        self.__temp_path_batches = None       
    
    def __drawgeodesicpaths(self, context, batchmaps):
        for batchmap in batchmaps:
            batch = batchmap.get('batch')
            batch_type = batchmap.get('type') or 'POINTS'
            self.shader.uniform_float('color', batchmap.get('color') or (1, 1, 1, 1))
            if('POINTS' in batch_type):
                bgl.glPointSize(batchmap.get('pointsize') or 5)
            if ('LINE' in batch_type):
                bgl.glLineWidth(batchmap.get('linewidth') or 5)
            batch.draw(self.shader)
        
        if(self.__temp_path_batches):
            for batchmap in self.__temp_path_batches:
                batch = batchmap.get('batch')
                batch_type = batchmap.get('type') or 'POINTS'
                self.shader.uniform_float('color', batchmap.get('color') or (1, 1, 1, 1))
                if('POINTS' in batch_type):
                    bgl.glPointSize(batchmap.get('pointsize') or 5)
                if ('LINE' in batch_type):
                    bgl.glLineWidth(batchmap.get('linewidth') or 5)
                batch.draw(self.shader)


    def __draw_callback_3d(self, op, context):        
        bgl.glEnable(bgl.GL_DEPTH_TEST);
        self.shader.bind()
        self.__drawgeodesicpaths(context, self.__drawbatches)

        batchmap = self.__mouse_cursor_batch
        self.shader.uniform_float('color', batchmap.get('color') or (1, 1, 1, 1))
        bgl.glPointSize(batchmap.get('pointsize') or 5)
        batchmap.get('batch').draw(self.shader)
        bgl.glDisable(bgl.GL_DEPTH_TEST);   

    def __register_handlers(self, args, context):
        self.__draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.__draw_callback_3d, args, 'WINDOW', 'POST_VIEW')
        self.__draw_event = context.window_manager.event_timer_add(0.1, window=context.window)
    
    def __unregister_handlers(self, context):
        context.window_manager.event_timer_remove(self.__draw_event)
        bpy.types.SpaceView3D.draw_handler_remove(self.__draw_handle, 'WINDOW')

        self.__draw_handle = None
        self.__draw_event = None
