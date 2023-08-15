import os
import subprocess
import json
from glob import fnmatch

from ij import IJ
from ij.plugin import ChannelSplitter

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
    IJ.log("Done")
        
def mark_dots(file_list_path, channels=[1,2,3], params_override={}):
    #results_path_pattern
    default_params = {
#       "image": imName 
        "mode": "Advanced",
        "anisotropy": 1.4,
        "robust_fitting": "[RANSAC]",
        "use_anisotropy": True,
        "image_min": 190,
        "image_max": 255,
        "sigma": 1.4,
        "threshold": 0.007,
        "support": 2,
        "min_inlier_ratio": 0.0,
        "max_error": 0.9,
        "spot_intensity_threshold": 0,
        "background": "[No background subtraction]",
        "background_subtraction_max_error": 0.05,
        "background_subtraction_min_inlier_ratio": 0.0,
#       "results_file": "[" + results_csv_path + "]",
        "use_multithreading": True,
        "num_threads": 40,
        "block_size_x": 128,
        "block_size_y": 128,
        "block_size_z": 16,
    }

    params = {}
    for ch in channels:
        params[ch] = default_params.copy()
        if ch in params_override:
            params[ch].update(params_override[ch])
    
    for file_path in open(file_list_path):
        file_path = file_path.strip()
        IJ.log("Opening image: " + file_path)
        imp = IJ.openImage(file_path)
        IJ.log("Splitting to channels")
        imp_channels = ChannelSplitter.split(imp)
        IJ.log("Using channels: " + channels)
        imp_channels = imp_channels[channels]

        for ch in channels:
            IJ.log("Processing channel {}".format(ch))
            imp_ch = imp_channels[ch]
            params_ch = params[ch]
            process_channel(imp_ch, params_ch)
        
def process_channel(imp, params):
    pass

file_list = create_file_list(directory, pattern)
#segment_nuclei_qupath(file_list, **params_override)
mark_dots(file_list)
