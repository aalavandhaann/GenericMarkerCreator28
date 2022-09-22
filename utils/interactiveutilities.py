import bpy, bmesh, bgl, math, os, mathutils, sys;
from mathutils import Vector;
import blf, time, datetime;
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_vector_3d, region_2d_to_location_3d, region_2d_to_origin_3d
from bpy_extras import view3d_utils;


def getViewports(context):    
    view_ports_count = 0;
    view_ports = [];
    
    for window in context.window_manager.windows:
        screen = window.screen;     
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                view_ports_count += 1;
                view_ports.append(area);
    
    return view_ports, view_ports_count;

def getActiveView(context, event):
    view_ports, view_ports_count = getViewports(context);
    region = None;
    rv3d = None;
    coord = event.mouse_x, event.mouse_y;
    for area in view_ports:
        for r in area.regions:
            if(r.type == "WINDOW" and r.x <= event.mouse_x < r.x + r.width and r.y <= event.mouse_y < r.y + r.height):
                rv3d = [space.region_3d for space in area.spaces if space.type == 'VIEW_3D'][0];
                region = r;
                coord = r.width - ((r.x + r.width) - event.mouse_x), r.height - ((r.y + r.height) - event.mouse_y);
                break;
    return region, rv3d, coord;

def ScreenPoint3D(context, event, *, ray_max=1000.0, position_mouse = True, use_mesh = None, bvh_tree=None):
    region, region3D, mouse_location = getActiveView(context, event)

    try:
        view_vector = view3d_utils.region_2d_to_vector_3d(region, region3D, mouse_location)
    except AttributeError:
        return None, None, None, None
    worldLocation3D = view3d_utils.region_2d_to_location_3d(region, region3D, mouse_location, view_vector)
    
    matrix_inv = use_mesh.matrix_world.inverted()

    worldLocation3D += view_vector.copy() * -1.0 * 1000.0
    
    #The 3D location converted in object local coordinates
    localLocation3D = matrix_inv @ worldLocation3D
    localViewVector3D = matrix_inv @ view_vector
    depsgraph = context.evaluated_depsgraph_get()
    depsgraph.update()

    
    # result, location, normal, face_index = use_mesh.ray_cast(localLocation3D, direction=localViewVector3D, depsgraph=depsgraph)
    location, normal, face_index, distance = bvh_tree.ray_cast(localLocation3D, localViewVector3D)
    # location, normal, face_index, distance = bvh_tree.find_nearest(localLocation3D)
    result = (location != None)
    
    # print(result, location, normal, face_index)
    return worldLocation3D, result, face_index, location