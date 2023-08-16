import os
import subprocess
import json
from glob import fnmatch
import shutil

from ij import IJ
from ij.plugin import ChannelSplitter

tmp_dir = os.environ['TMPDIR']
directory = "/Users/hkariti/repo/technion/fish_join/data_files"
pattern = "*_MAX.tif"
nuclei_params_override = json.loads('{}')
nuclei_channel = 4
dots_channels = [1,2,3]
dots_params_override = json.loads('{}')
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


class QuPathSegmentor:
    def __init__(self, channel, qupath_executable='QuPath', tmp_dir='/tmp', script_dir='.', keep_project_dir=False):
        self.channel = channel
        self.qupath_exeuctable = qupath_executable
        self.tmp_dir = tmp_dir
        self.script_dir = script_dir
        self._qupath_project_filename = 'project.qpproj'
        self.keep_project_dir = keep_project_dir

    def qupath_script(self, script_name, project=None, args=[]):
        script_path = os.path.join(self.script_dir, script_name)
        cmdline = [self.qupath_executable, 'script', script_path]
        if project is not None:
            if os.path.isdir(project):
                project = os.path.join(project, self._qupath_project_filename)
            cmdline += ['-p', project]
        for a in args:
            cmdline += ['-a', a]
        try:
            subprocess.check_call(cmdline)
        except subprocess.CalledProcessError as e:
            IJ.log("QuPathSegmentor: Failed to run script {}, errcode {}".format(script_name, e.returncode))
            raise

    def run(self, file_list_path, params_override={}):
        params = {"detectionImage": "Channel {}".format(self.channel), 
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

        qupath_project = os.path.join(self.tmp_dir, 'qupath')
        IJ.log("QuPathSegmentor: creating QuPath project")
        qupath_script('qupath_create_project.groovy', args=[file_list_path, qupath_project])
        IJ.log("QuPathSegmentor: detecting nuclei")
        qupath_script( 'qupath_get_nuclei.groovy', args=[params_json], project=qupath_project)
        if not self.keep_project_dir:
            IJ.log("QuPathSegmentor: cleaning up QuPath project")
            shutil.rmtree(qupath_project)
        IJ.log("QuPathSegmentor: done")
        

class RSFISHSegmentor:
    def __init__(self, channels, result_file_pattern="{image_dir}/{image_title}_C{channel}.csv"):
        self.channels = channels
        self.result_file_pattern = result_file_pattern

    def run(self, file_list_path, params_override={}):
        default_params = {
    #       "image": imName 
            "mode": "Advanced",
            "anisotropy": 1.0,
            "robust_fitting": "[RANSAC]",
            "compute_min/max": True,
            "use_anisotropy": True,
            "spot_intensity": "[Linear Interpolation]",
            "sigma": 1.4310,
            "threshold": 0.00219,
            "support": 3,
            "min_inlier_ratio": 0.10,
            "max_error": 1.5,
            "spot_intensity_threshold": 3094.59,
            "background": "[No background subtraction]",
            "background_subtraction_max_error": 0.05,
            "background_subtraction_min_inlier_ratio": 0.10,
    #       "results_file": "[" + results_csv_path + "]",
            "use_multithreading": True,
            "num_threads": 10,
            "block_size_x": 128,
            "block_size_y": 128,
            "block_size_z": 16,
        }

        params = {}
        for ch in self.channels:
            params[ch] = default_params.copy()
            if ch in params_override:
                params[ch].update(params_override[ch])
        
        for file_path in open(file_list_path):
            file_path = file_path.strip()
            image_dir = os.path.dirname(file_path)
            IJ.log("RSFISHSegmentor: opening image: " + file_path)
            imp = IJ.openImage(file_path)
            image_title = imp.getShortTitle()
            IJ.log("RSFISHSegmentor: {}: splitting to channels".format(image_title))
            imp_channels = ChannelSplitter.split(imp)
            IJ.log("RSFISHSegmentor: {}: image has {} channels, will use {}".format(image_title, len(imp_channels), self.channels))

            for ch in self.channels:
                IJ.log("RSFISHSegmentor: {}: processing channel {}".format(image_title, ch))
                imp_ch = imp_channels[ch-1]
                params_ch = params[ch]
                result_file_path = self.result_file_pattern.format(image_dir=image_dir, image_title=image_title, channel=ch)
                IJ.log("RSFISHSegmentor: {}: channel {}: saving to {}".format(image_title, ch, result_file_path))
                self.process_channel(imp_ch, result_file_path, params_ch)
            IJ.log("RSFISHSegmentor: {}: done".format(image_title))
        IJ.log("RSFISHSegmentor: finished processing all images")
            
    def process_channel(self, imp, results_file, params):
        params['results_file'] = [results_file]
        #params['image'] = "08_A08.nd2_MAX.tif"
        params_str = self._create_param_string(params)

        imp.show()
        IJ.run(imp, "RS-FISH", params_str)
        imp.hide()

    def _create_param_string(self, params):
        param_str = ''
        for key, value in params.items():
            if type(value) is bool and value:
                param_str += '{} '.format(key)
            elif type(value) in [list, tuple]:
                assert len(value) == 1 # The list is to mark that this is a choice from a drop-down, not to hold several values
                param_str += '{}=[{}] '.format(key, value[0])
            elif type(value) is float:
                param_str += '{}={:.4f} '.format(key, value)
            else:
                param_str += '{}={} '.format(key, value)

        return param_str.strip()
                

file_list = create_file_list(directory, pattern)
nuclei_segmentor = QuPathSegmentor(nuclei_channel, qupath_executable, tmp_dir, script_dir)
#nuclei_segmentor.run(file_list, params_override=nuclei_params_override)
dots_segmentor = RSFISHSegmentor(channels=dots_channels)
dots_segmentor.run(file_list, params_override=dots_params_override)
