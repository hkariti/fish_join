import os
import subprocess
import json
from glob import fnmatch

import il import IJ

tmp_dir = os.environ['TMPDIR']
directory = "/Users/hkariti/repo/technion/fish_join/data_files"
pattern = "*_MAX.tif"
params_override = json.loads('{}')
qupath_executable = '/Applications/QuPath.app/Contents/MacOS/QuPath'

script_dir = '/Users/hkariti/repo/technion/fish_join'

def create_file_list(directory, pattern):
	file_list_path = os.path.join(tmp_dir, 'qupath_file_list')
	file_list = open(file_list_path, 'w')
	for path, _, filenames in os.walk(directory):
		for filename in filenames:
			if not fnmatch.fnmatch(filename, pattern):
				continue
			image_path = path + os.path.sep + filename
			file_list.write(image_path + '\n')
	file_list.close()
	
	return file_list_path

def qupath_script(script_name, project=None, args=[]):
    cmdline = [qupath_executable, 'script', os.path.join(script_dir, script_name)]
    if project is not None:
        if os.path.isdir(project):
            project = os.path.join(project, 'project.qpproj')
        cmdline += ['-p', project]
    for a in args:
        cmdline += ['-a', a]
    try:
        subprocess.check_call(cmdline)
    except subprocess.CalledProcessError as e:
        IJ.log("Failed to run script {}, errcode {}".format(script_name, e.returncode))
        raise

def segment_nuclei_qupath(file_list_path, params_override={}):
    params = {"detectionImage": "Channel 4", 
              "requestedPixelSizeMicrons": 0.0, 
              "backgroundRadiusMicrons": 8.0, 
              "backgroundByReconstruction": True, 
              "medianRadiusMicrons": 0.0, 
              "sigmaMicrons": 1.5, 
              "minAreaMicrons": 10.0, 
              "maxAreaMicrons": 400.0, 
              "threshold": 100.0, 
              "watershedPostProcess": True, 
              "cellExpansionMicrons": 5.0, 
              "includeNuclei": True, 
              "smoothBoundaries": True, 
              "makeMeasurements": True }
    params.update(params_override)
    params_json = json.dumps(params)

    qupath_project = os.path.join(tmp_dir, 'qupath')
    IJ.log("Creating QuPath project")
    qupath_script('qupath_create_project.groovy', args=[file_list, qupath_project])
    IJ.log("Detecting nuclei")
    qupath_script( 'qupath_get_nuclei.groovy', args=[params_json], project=qupath_project)
        

file_list = create_file_list(directory, pattern)
segment_nuclei_qupath(file_list, **params_override)
