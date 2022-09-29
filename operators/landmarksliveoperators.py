from multiprocessing.sharedctypes import Value
import bpy, bmesh, time;
from bpy.props import StringProperty;
from bpy.props import FloatVectorProperty;
from mathutils import Vector, Matrix;
from mathutils.bvhtree import BVHTree;
from scipy.io import loadmat;
from sklearn.neighbors import NearestNeighbors

import bgl
import gpu
from gpu_extras.batch import batch_for_shader



from GenericMarkerCreator28 import constants;
from GenericMarkerCreator28.properties import changeMarkerColor, changeUnlinkedMarkerColor;
from GenericMarkerCreator28.utils.bgl_utilities import getPointBatch, getHollowCircleBatch
from GenericMarkerCreator28.utils.interactiveutilities import ScreenPoint3D;
from GenericMarkerCreator28.utils.staticutilities import detectMN, applyMarkerColor, addConstraint, getConstraintsKD, deleteObjectWithMarkers, reorderConstraints;
from GenericMarkerCreator28.utils.staticutilities import getMarkersForMirrorX, getGenericLandmark, getMeshForBlenderMarker, getBlenderMarker;
from GenericMarkerCreator28.utils.meshmathutils import getBarycentricCoordinateFromPolygonFace, getBarycentricCoordinate, getBarycentricCoordinateFromIndices, getCartesianFromBarycentre, getGeneralCartesianFromBarycentre, getTriangleArea;
from GenericMarkerCreator28.utils.mathandmatrices import getObjectBounds;
from GenericMarkerCreator28.utils.mathandmatrices import getBMMesh, ensurelookuptable;
# def DrawGL(self, context):
    
#     bgl.glDisable(bgl.GL_DEPTH_TEST);
#     bgl.glColor(1.0, 1.0, 0.0, 1.0);
    
#     for (co, id) in self.M_markers:
#         drawPoint(Vector((0,0,0)), (1,1,1,1), size=15.0);
#         drawHollowCircleBillBoard(context, co, self.marker_ring_size);
#         drawText(context, "id: %d"%(id), co, text_scale_value = 0.001, constant_scale = False);
        
#     for (co, id) in self.N_markers:
#         drawPoint(Vector((0,0,0)), (1,1,1,1));
#         drawHollowCircleBillBoard(context, co, self.marker_ring_size);
#         drawText(context, "id: %d"%(id), co, text_scale_value = 0.001, constant_scale = False);
    
#     # restore opengl defaults
#     bgl.glLineWidth(1);
#     bgl.glDisable(bgl.GL_BLEND);
#     bgl.glEnable(bgl.GL_DEPTH_TEST);
#     bgl.glColor(0.0, 0.0, 0.0, 1.0);


class LiveLandmarksCreator(bpy.types.Operator):
    """Draw a line with the mouse"""
    bl_idname = "genericlandmarks.livelandmarkscreator";
    bl_label = "Landmarks Creator";
    bl_description = "Create Landmarks for surface(s)"
    hit: FloatVectorProperty(name="hit", size=3);

    def __init__(self)    :
        self.__draw_handle = None
        self.__draw_event = None
        self.__widgets = []

    def getPolygonBarycenter(self, context, the_mesh, the_evaluated_mesh, face_index, hitpoint):
        face = the_mesh.data.polygons[face_index];
        loops = the_mesh.data.loops;
        vertices = the_evaluated_mesh.data.vertices;
        a = vertices[loops[face.loop_indices[0]].vertex_index];
        b = vertices[loops[face.loop_indices[1]].vertex_index];
        c = vertices[loops[face.loop_indices[2]].vertex_index];
        d = None
        isinside = False
        if(len(face.loop_indices) > 3):
            d = vertices[loops[face.loop_indices[3]].vertex_index];
        
        area, area2 = getTriangleArea(a.co, b.co, c.co);
        # u,v,w,ratio,isinside = getBarycentricCoordinate(hitpoint, a.co, b.co, c.co, epsilon=area * 0.1, snapping=the_mesh.snap_landmarks);
        u,v,w,ratio,isinside = getBarycentricCoordinateFromIndices(hitpoint, the_evaluated_mesh, [a.index, b.index, c.index], epsilon=area * 0.1, snapping=the_mesh.snap_landmarks);
        
        if(d and not isinside):
            area, area2 = getTriangleArea(c.co, d.co, a.co);
            # u,v,w,ratio,isinside = getBarycentricCoordinate(hitpoint, c.co, d.co, a.co, epsilon=area * 0.1, snapping=the_mesh.snap_landmarks);
            u,v,w,ratio,isinside = getBarycentricCoordinateFromIndices(hitpoint, the_evaluated_mesh, [c.index, d.index, a.index], epsilon=area * 0.1, snapping=the_mesh.snap_landmarks);
            return u, v, w, c, d, a, isinside, face

        return u, v, w, a, b, c, isinside, face

    
    def modal(self, context, event):
        if(self.__m_total_markers != len(self.M.generic_landmarks) or self.__n_total_markers != len(self.N.generic_landmarks)):
            self.__updateMarkerDrawingBatches(context)

        if event.type in {'ESC'}:
            # context.area.header_text_set(text="");
            bpy.ops.object.select_all(action="DESELECT");
            if(self.mousepointer):
                self.mousepointer.hide_select = False
                self.mousepointer.select_set(True);
                context.view_layer.objects.active = self.mousepointer;
                bpy.ops.object.delete();
            self.__finish(context)
            return {'CANCELLED'}

        elif (event.type in {"A", "a"} and event.value in {"PRESS"}):
            self.hit, onM, m_face_index, m_hitpoint = ScreenPoint3D(context, event, position_mouse = False, use_mesh=self.M, bvh_tree=self.bvhtree_m);
            self.hit, onN, n_face_index, n_hitpoint = ScreenPoint3D(context, event, position_mouse = False, use_mesh=self.N, bvh_tree=self.bvhtree_n);
            

            the_mesh = None;
            the_evaluated_mesh = None
            face_index = -1;
            hitpoint = None;
            use_bvh_tree = None;
            onMesh = False;
            
            if(onM):
                the_mesh = self.M;
                the_evaluated_mesh = self.M_eval
                face_index = m_face_index;
                hitpoint = m_hitpoint;
                use_bvh_tree = self.bvhtree_m;
                onMesh = onM;
            if(onN):
                the_mesh = self.N;
                the_evaluated_mesh = self.N_eval
                face_index = n_face_index;
                hitpoint = n_hitpoint;
                use_bvh_tree = self.bvhtree_n;
                onMesh = onN;

            if(face_index and onMesh):
                proceedToAddMarker = False;                
                diffmouse = time.time() - self.lastmousepress;
                
                if(diffmouse > constants.TIME_INTERVAL_MOUSE_PRESS and onMesh):
                    self.lastmousepress = time.time();
                    markerskd, markercos = getConstraintsKD(context, the_mesh);
                    co, index, dist = markerskd.find(hitpoint);
                    if(not len(the_mesh.generic_landmarks)):
                        dist = 9999999.0;
                        
                    if(dist):
                        if(dist > constants.MARKER_MIN_DISTANCE):
                            proceedToAddMarker = True;
                        else:
                            proceedToAddMarker = False;
                
                print('Proceed to add marker: %s, face index: %s, On Mesh: %s'%(proceedToAddMarker, face_index, onMesh) )
                if(proceedToAddMarker):
                    u, v, w, a, b, c, isinside, face = self.getPolygonBarycenter(context, the_mesh, the_evaluated_mesh, face_index, hitpoint)
                    finalPoint = getCartesianFromBarycentre(Vector((u,v,w)), a.co, b.co, c.co);
                    
                    print('PROCEED TO ADD MARKER : %s, IS INSIDE : %s'%(proceedToAddMarker, isinside));
                    if(isinside):
                        print('ADDING MARKER WITH BARYCENTRIC VALUES ::: ',u,v,w, face.index);
                        addConstraint(context, the_mesh, [u,v,w], [a.index, b.index, c.index], hitpoint, faceindex=face_index);                        
                        if(context.scene.use_mirrormode_x):
                            center = finalPoint.copy();
                            print(finalPoint, hitpoint)
                            center.x = -center.x;
                            print(center, hitpoint)
                            delta = (finalPoint - center).length;
                            print('DELTA BETWEEN SYMMETRY POINTS ', delta);
                            if(delta > constants.EPSILON):
                                try:
                                    co, n, index, distance = use_bvh_tree.find(center);
                                except AttributeError:
                                    co, n, index, distance = use_bvh_tree.find_nearest(center);
                                
                                face = the_mesh.data.polygons[index];a

                                u, v, w, a, b, c, isinside, face = self.getPolygonBarycenter(context, the_mesh, the_evaluated_mesh, face.index, co)
                                finalPoint = getCartesianFromBarycentre(Vector((u,v,w)), a.co, b.co, c.co);
                                addConstraint(context, the_mesh, [u,v,w], [a.index, b.index, c.index], co, faceindex=face.index);
                                print('ADD MIRROR MARKER AT ', center, u, v, w);
                                print('IT HAS A NEAREST FACE : ', index, ' AT A DISTANCE ::: ', distance);
                        
                        self.__updateMarkerDrawingBatches(context)
                
                        del self.M_markers[:];
                        del self.N_markers[:];
                        
                        for gm in self.M.generic_landmarks:
                            loc = Vector([dim for dim in gm.location]);
                            loc = self.M.matrix_world @ loc;
                            dictio = (loc, gm.id);
                            self.M_markers.append(dictio);
                        
                        if(self.M != self.N and self.N):
                            for gm in self.N.generic_landmarks:
                                loc = Vector([dim for dim in gm.location]);
                                loc = self.N.matrix_world @ loc;
                                dictio = (loc, gm.id);
                                self.N_markers.append(dictio);

            return {'RUNNING_MODAL'};

            
        elif event.type == 'MOUSEMOVE':    
            try:
                self.hit, onM, m_face_index, m_hitpoint = ScreenPoint3D(context, event, position_mouse = False, use_mesh=self.M, bvh_tree = self.bvhtree_m);
                self.hit, onN, n_face_index, n_hitpoint = ScreenPoint3D(context, event, position_mouse = False, use_mesh=self.N, bvh_tree = self.bvhtree_n);
            except ValueError:
                return {'RUNNING_MODAL'}

            the_mesh = None;
            the_evaluated_mesh = None;
            face_index = -1;
            hitpoint = None;
            
            if(onM):
                the_mesh = self.M;
                the_evaluated_mesh = self.M_eval
                face_index = m_face_index;
                hitpoint = m_hitpoint;
            elif (onN):
                the_mesh = self.N;
                the_evaluated_mesh = self.N_eval
                face_index = n_face_index;
                hitpoint = n_hitpoint;
#             context.area.header_text_set("hit: %.4f %.4f %.4f" % tuple(self.hit));
            if(onM or onN):
                if(face_index):
                    u, v, w, a, b, c, isinside, face = self.getPolygonBarycenter(context, the_mesh, the_evaluated_mesh, face_index, hitpoint,)
                    newco = getCartesianFromBarycentre(Vector((u,v,w)), a.co, b.co, c.co);
                    # context.area.header_text_set("Barycentric Values: %.8f %.8f %.8f %.8f" % tuple((u,v,w,(u+v+w))));                        
                    self.mousepointer.location = the_mesh.matrix_world @ newco;
                else:
                    print('NO VALID POSITION')
        
        return {'PASS_THROUGH'};
        
    def invoke(self, context, event):
        if(not context.active_object or context.active_object.type != 'MESH'):
            self.report({'ERROR'}, 'Select a mesh to add landmarks');
            return {'CANCELLED'};
        if(context.active_object):
            M, N = detectMN(context.active_object);
            if(not M and not N):
                self.M = context.active_object;
                self.N = context.active_object;
            elif(M and not N):
                self.M = M;
                self.N = M;
            elif (not M and N):
                self.M = N;
                self.N = N;
            else:
                self.M = M;
                self.N = N;
            
        self.lastkeypress = time.time();
        self.lastmousepress = time.time();
        
        self.mesh = context.active_object;


        # Get their world matrix
        mat1 = self.M.matrix_world
        mat2 = self.N.matrix_world

        # Get the geometry in world coordinates
        vert1 = [mat1 @ v.co for v in self.M.data.vertices] 
        poly1 = [p.vertices for p in self.M.data.polygons]

        vert2 = [mat2 @ v.co for v in self.N.data.vertices] 
        poly2 = [p.vertices for p in self.N.data.polygons]

        depsgraph = context.evaluated_depsgraph_get()
        depsgraph.update()

        self.M_eval = self.M.evaluated_get(depsgraph)
        self.N_eval = self.N.evaluated_get(depsgraph)

        m_bmesh = bmesh.new()
        n_bmesh = bmesh.new()

        m_bmesh.from_object(self.M, depsgraph)
        n_bmesh.from_object(self.N, depsgraph)

        ensurelookuptable(m_bmesh)
        ensurelookuptable(n_bmesh)

        # m_evaluated = self.M.evaluated_get(depsgraph).to_mesh()
        # print(m_evaluated)

        # self.bvhtree_m = BVHTree.FromPolygons( vert1, poly1 )
        # self.bvhtree_n = BVHTree.FromPolygons( vert2, poly2 )

        # self.bvhtree_m = BVHTree.FromObject( self.M, depsgraph )
        # self.bvhtree_n = BVHTree.FromObject( self.N, depsgraph )

        self.bvhtree_m = BVHTree.FromBMesh( m_bmesh)
        self.bvhtree_n = BVHTree.FromBMesh( n_bmesh)

        m_bmesh.free()
        n_bmesh.free();

        self.use_bvhtree = self.bvhtree_m
        
        self.M_markers = [];
        self.N_markers = [];
        
        for gm in self.M.generic_landmarks:
            loc = Vector([dim for dim in gm.location]);
            loc = self.M.matrix_world @ loc;
            dictio = (loc, gm.id);
            self.M_markers.append(dictio);
        
        if(self.M != self.N and self.N is not None):
            for gm in self.N.generic_landmarks:
                loc = Vector([dim for dim in gm.location]);
                loc = self.N.matrix_world @ loc;
                dictio = (loc, gm.id);
                self.N_markers.append(dictio);
        
        maxsize = max(self.mesh.dimensions.x, self.mesh.dimensions.y, self.mesh.dimensions.z);
        markersize = maxsize * 0.025;            
        tempmarkersource = "Marker";
        
        try:
            tempmarker = bpy.data.objects[tempmarkersource];
        except KeyError:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=36, ring_count = 36);
            tempmarker = context.object;
            tempmarker.name = "Marker";

        tempmarker.dimensions = (markersize,markersize,markersize);
        tempmarker.hide_select = True
        self.mousepointer = tempmarker;
        
        real_marker = None;
        try:
            real_marker = context.scene.objects[context.scene.landmarks_use_selection];
        except KeyError:
            real_marker = tempmarker;
            
        min_size, max_size = getObjectBounds(real_marker);
        size_vector = max_size - min_size;
        
        self.__m_total_markers = len(self.M.generic_landmarks)
        self.__n_total_markers = len(self.N.generic_landmarks)

        self.marker_ring_size = size_vector.length * 0.009;        
        self.key = [];
        self.time = [];
        
        applyMarkerColor(self.mousepointer);
        context.view_layer.objects.active = self.mesh;
        
        self.__create_shader()
        self.m_draw_batches = []
        self.n_draw_batches = []
        self.__updateMarkerDrawingBatches(context)
        args = (self, context)
        self.__register_handlers(args, context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'};

    def __create_shader(self):
        '''
            https://docs.blender.org/api/current/gpu.shader.html?highlight=from_builtin#gpu.shader.from_builtin
            for different builtin drawing methods
            essentially you created different shaders to draw different types of drawings
        '''
        self.shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

    def __getMarkerBatchesForMesh(self, context, mesh):
        batches_list = []
        for m_mkr in mesh.generic_landmarks:
            color = (1, 0, 0, 1)
            if(m_mkr.is_linked):
                color = (mesh.linked_landmark_color[0], mesh.linked_landmark_color[1], mesh.linked_landmark_color[2], 1.0)
            else:
                color = (mesh.unlinked_landmark_color[0], mesh.unlinked_landmark_color[1], mesh.unlinked_landmark_color[2], 1.0)
            mkr_co = mesh.matrix_world @ Vector(m_mkr.location)
            face = mesh.data.polygons[m_mkr.faceindex]
            point_batch = getPointBatch(context, self.shader, mkr_co, color=color)
            hollow_circle_batch = getHollowCircleBatch(context, self.shader, mkr_co, face.normal, radius=self.marker_ring_size, resolution=20, color=color, linewidth=5)
            batches_list.append(point_batch)
            batches_list.append(hollow_circle_batch)

        return batches_list

    def __updateMarkerDrawingBatches(self, context):
        del self.m_draw_batches[:]
        del self.n_draw_batches[:]

        self.__m_total_markers = len(self.M.generic_landmarks) 
        self.__n_total_markers = len(self.N.generic_landmarks)

        m_batches = self.__getMarkerBatchesForMesh(context, self.M)
        self.m_draw_batches.extend(m_batches)
        if(self.M != self.N):
            n_batches = self.__getMarkerBatchesForMesh(context, self.N)
            self.n_draw_batches.extend(n_batches)

    def __finish(self, context):
        self.__unregister_handlers(context)
        return {'FINISHED'}

    def __drawMarkerBatches(self, context, batchmaps):

        for batchmap in batchmaps:
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
        # self.shader.uniform_float('color', (1, 1, 1, 1))        
        self.__drawMarkerBatches(context, self.m_draw_batches)
        self.__drawMarkerBatches(context, self.n_draw_batches)
        bgl.glDisable(bgl.GL_DEPTH_TEST);   


    def __register_handlers(self, args, context):
        self.__draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.__draw_callback_3d, args, 'WINDOW', 'POST_VIEW')
        self.__draw_event = context.window_manager.event_timer_add(0.1, window=context.window)
    
    def __unregister_handlers(self, context):
        context.window_manager.event_timer_remove(self.__draw_event)
        bpy.types.SpaceView3D.draw_handler_remove(self.__draw_handle, 'WINDOW')

        self.__draw_handle = None
        self.__draw_event = None







