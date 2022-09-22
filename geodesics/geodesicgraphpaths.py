import sys, time, math;
from mathutils import Vector;

import bpy;
from GenericMarkerCreator28.utils.mathandmatrices import getBMMesh, ensurelookuptable
__fastAlgorithm = False;
try:
	import py_chenhancc;
	from py_chenhancc import CRichModel as RichModel, CICHWithFurtherPriorityQueue, CPoint3D, CFace;
	__fastAlgorithm = True;
except ImportError:
	from GenericMarkerCreator28.utils.geodesics.CICHWithFurtherPriorityQueue import CICHWithFurtherPriorityQueue

import numpy as np;
from mathutils import Vector, Color;

def isFastAlgorithmLoaded():
	return __fastAlgorithm;


class GraphPaths:
    # Reference to the blender object;
    m_mesh = None;
    # Reference to the bm_data;
    m_bmesh = None;
    # Reference to the blender context;
    m_context = None;
    # indices of seed paths;
    m_seed_indices = None;
    
    def __init__(self, context, mesh, bm_mesh):
        self.m_mesh = mesh;
        self.m_bmesh = bm_mesh;
        self.m_context = context;
        self.m_seed_indices = [];
    
    def removeSeedIndex(self, seed_index):
        try:
            index = self.m_seed_indices.index(seed_index);
            self.m_seed_indices.remove(seed_index);
            return index;
        except ValueError:
            return -1;
    
    def addSeedIndex(self, seed_index, passive=False):
        try:
            self.m_seed_indices.index(seed_index);
        except ValueError:
            self.m_seed_indices.append(seed_index);
    
    def path_between(self, seed_index, target_index, local_path=False):        
        return [];
      
    def path_between_raw(self, seed_index, target_index):        
        return [];
    
    def getSeedIndices(self):
        return self.m_seed_indices;
    
    def getVertexDistances(self, seed_index):
    	return [];

	
class ChenhanGeodesics(GraphPaths):
    
    m_all_geos = None;
    m_richmodel = None;
    algo = None;
    
    def __init__(self, context, mesh, bm_mesh, richmodel):
        super().__init__(context, mesh, bm_mesh);
        self.m_all_geos = [];
        print('DO YOU HAVE THE FAST VERSION ? ', isFastAlgorithmLoaded());
        
        if(isFastAlgorithmLoaded()):
        	print('CREATE RICHMODEL USING C');
        	verts = [];
        	faces = [];
        	loops = mesh.data.loops;
        	self.m_richmodel = RichModel();
        	print('CREATE RICHMODEL USING C FOR VERTICES');
        	for v in mesh.data.vertices:
        		p3d = CPoint3D(v.co.x, v.co.y, v.co.z);
        		verts.append(p3d);
        	print('CREATE RICHMODEL USING C FOR POLYGONS');
        	for f in mesh.data.polygons:
        		f_vids = [loops[lid].vertex_index for lid in f.loop_indices];
        		faces.append(CFace(f_vids[0], f_vids[1], f_vids[2]));
        	print('RICHMODEL LOAD THE MODEL');
        	self.m_richmodel.LoadModel(verts, faces);
        	print('RICHMODEL PREPROCESS');
        	self.m_richmodel.Preprocess();
        else:
        	self.m_richmodel = richmodel;
        
        print('ENSURE LOOKUP TABLE');
        ensurelookuptable(bm_mesh);

    def getRichModel(self):
    	return self.m_richmodel;
    
    def getVertexDistances(self, seed_index):
    	try:
    		indice = self.m_seed_indices.index(seed_index);
    		if(not self.m_all_geos[indice]):
    			if(isFastAlgorithmLoaded()):
    				alg = CICHWithFurtherPriorityQueue(self.m_richmodel, set([seed_index]));
    			else:
    				alg = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[seed_index]);
    			alg.Execute();
    		alg = self.m_all_geos[indice];
    		return [iav.disUptodate for iav in alg.GetVertexDistances()];
    	except ValueError:
    		print("THE intended seed_index does not exist, so returning NONE");
    		return None;
    
    def addSeedIndex(self, seed_index, passive=False, log=False):
        super().addSeedIndex(seed_index);
        index = self.m_seed_indices.index(seed_index);
        if(not passive):
            try:
                geos_index = self.m_all_geos[index];
            except IndexError:
                alg = None;
                start = time.time();
                if(isFastAlgorithmLoaded()):
                	alg = CICHWithFurtherPriorityQueue(self.m_richmodel, set([seed_index]));
                else:
                	alg = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[seed_index]);
                alg.Execute();
                end = time.time();
                if(log):
                	print('TOTAL TIME FOR SEEDING ::: ', (end - start), " seconds");
                self.m_all_geos.append(alg);
#                 self.m_all_geos.append(self.algo);
        else:
            self.m_all_geos.append(None);
    
    def removeSeedIndex(self, seed_index):
        removed_index = super().removeSeedIndex(seed_index);
        if(removed_index != -1):
            del self.m_all_geos[removed_index];
    
    #Always returns the path in reverse i.e from the target to the seed
    def path_between(self, seed_index, target_index, local_path=True):
        try:
            indice = self.m_seed_indices.index(seed_index);
            
            if(not self.m_all_geos[indice]):
                if(isFastAlgorithmLoaded()):
                	alg = CICHWithFurtherPriorityQueue(self.m_richmodel, set([seed_index]));
                else:
                 	alg = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[seed_index]);
                alg.Execute();
#                 self.m_all_geos[indice] = alg;
#                 ensurelookuptable(self.m_bmesh);
#                 self.algo = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[v.index for v in self.m_bmesh.verts]);
#                 self.algo.Execute();
#                 self.m_all_geos[indice] = self.algo;
            
            if(isFastAlgorithmLoaded()):
            	pathp3d = self.m_all_geos[indice].FindSourceVertex(target_index, []);
            else:
            	pathp3d, sourceindex = self.m_all_geos[indice].FindSourceVertex(target_index);
            path = [];
#             print('SOURCE INDEX ::: ', sourceindex, ' GIVEN SEED INDEX ::: ', seed_index, ' GIVEN TARGET INDEX ', target_index);
#             print('TABLE OF RESULTING PATHS ::: ');
#             print(self.algo.m_tableOfResultingPaths);
            
            for eitem in pathp3d:
            	vco = eitem.Get3DPoint(self.m_richmodel);
            	if(isFastAlgorithmLoaded()):
            		vco = Vector((vco.x, vco.y, vco.z));
            	if(not local_path):
            		path.append(self.m_mesh.matrix_world @ vco);
            	else:
            		path.append(vco);
            
            return path;
        
        except ValueError:
            print("THE intended seed_index does not exist, so returning NONE");
            return None;
           
    def path_between_raw(self, seed_index, target_index, local_path=True):
	    try:
	        indice = self.m_seed_indices.index(seed_index);            
        	if(not self.m_all_geos[indice]):
		        if(isFastAlgorithmLoaded()):
		            alg = CICHWithFurtherPriorityQueue(self.m_richmodel, set([seed_index]));
		        else:
		            alg = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[seed_index]);
		        alg.Execute();
		     
	        if(isFastAlgorithmLoaded()):
		        pathp3d = self.m_all_geos[indice].FindSourceVertex(target_index, []);
	        else:
	        	pathp3d, sourceindex = self.m_all_geos[indice].FindSourceVertex(target_index);
	        
	        return pathp3d;
	    except ValueError:
		    print("THE intended seed_index does not exist, so returning NONE");
		    return None;