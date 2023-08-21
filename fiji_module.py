import os
import subprocess
import csv
import json
from glob import fnmatch
import shutil

from ij import IJ
from ij.plugin import ChannelSplitter

import join

tmp_dir = os.environ['TMPDIR']
directory = "/Users/hkariti/repo/technion/fish_join/data_files"
pattern = "*_MAX.tif"
nuclei_params_override = json.loads('{}')
nuclei_channel = 4
dots_channels = [1,2,3]
dots_params_override = json.loads('{}')
qupath_executable = '/Applications/QuPath.app/Contents/MacOS/QuPath'
script_dir = '/Users/hkariti/repo/technion/fish_join'

image_join_output_pattern = '{image_path}_nuclei_dots_joined.csv'
image_nuclei_output_pattern = '{image_path}_nuclei.json'
global_join_output_filename = 'nuclei_dots_joined.csv'
global_nuclei_output_filename = 'nuclei.json'


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
    _default_params = {"detectionImage": "Channel {channel}", 
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

    def __init__(self, channel, qupath_executable='QuPath', tmp_dir='/tmp', script_dir='.', keep_project_dir=False, params_override={}):
        self.channel = channel
        self.qupath_executable = qupath_executable
        self.tmp_dir = tmp_dir
        self.script_dir = script_dir
        self._qupath_project_filename = 'project.qpproj'
        self.keep_project_dir = keep_project_dir

        params = self._default_params.copy()
        params.update(params_override)
        params['detectionImage'] = params['detectionImage'].format(channel=channel)
        self.params_json = json.dumps(params)

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

    def process_file_list(self, file_list_path):
        qupath_project = os.path.join(self.tmp_dir, 'qupath')
        IJ.log("QuPathSegmentor: creating QuPath project")
        self.qupath_script('qupath_create_project.groovy', args=[file_list_path, qupath_project])
        IJ.log("QuPathSegmentor: detecting nuclei")
        self.qupath_script( 'qupath_get_nuclei.groovy', args=[self.params_json], project=qupath_project)
        if not self.keep_project_dir:
            IJ.log("QuPathSegmentor: cleaning up QuPath project")
            shutil.rmtree(qupath_project)
        IJ.log("QuPathSegmentor: done")

    def get_image_nuclei(self, image_path):
        """
        Return a list of nuclei in the image. Each nucleus object has
        an ID and a list of polygon edges
        """
        nuclei_file = self._get_output_filename(image_path)

        return self._parse_nuclei_geojson(nuclei_file)

    def _parse_nuclei_geojson(self, geojson):
        """
        Parse QuPath's geojson file and return a list of dicts with
        each nucleus' ID and polygon vertices.

        geojson can be either a path to a filename, an open geojson file
        or a parsed geojson as a dict object.
        """
        if isinstance(geojson, (str, unicode)):
            _geojson = json.load(open(geojson))
        elif isinstance(geojson, file):
            _geojson = json.load(geojson)
        else:
            _geojson = geojson

        nuclei = []
        index = 0
        for feature in _geojson['features']:
            try:
                if feature['properties']['objectType'] != 'cell':
                    continue
            except KeyError:
                continue
            try:
                polygon = feature['nucleusGeometry']['coordinates'][0]
                nuclei.append(dict(id=index, polygon=polygon))
            except (KeyError, IndexError):
                IJ.log("parse_nuclei_geojson: nuclei {} is bad, skipping".format(index))
                continue
            finally:
                index += 1

        return nuclei

    def _get_output_filename(self, image_file_path):
        filename = os.path.splitext(image_file_path)[0]

        return filename + '_nuclei.geojson'


class RSFISHSegmentor:
    _default_params = {
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
        "use_multithreading": True,
        "num_threads": 10,
        "block_size_x": 128,
        "block_size_y": 128,
        "block_size_z": 16,
    }

    def __init__(self, channels, result_file_pattern="{image_dir}/{image_title}_C{channel}.csv", params_override={}):
        self.channels = channels
        self.result_file_pattern = result_file_pattern

        self.params = {}
        for ch in self.channels:
            self.params[ch] = self._default_params.copy()
            if ch in params_override:
                self.params[ch].update(params_override[ch])

    def process_image(self, file_path):
        image_dir = os.path.dirname(file_path)
        IJ.log("RSFISHSegmentor: opening image: " + file_path)
        imp = IJ.openImage(file_path)
        image_title = imp.getShortTitle()
        IJ.log("RSFISHSegmentor: {}: splitting to channels".format(image_title))
        imp_channels = ChannelSplitter.split(imp)
        IJ.log("RSFISHSegmentor: {}: image has {} channels, will use {}".format(image_title, len(imp_channels), self.channels))

        output_filenames = []
        for ch in self.channels:
            IJ.log("RSFISHSegmentor: {}: processing channel {}".format(image_title, ch))
            imp_ch = imp_channels[ch-1]
            params_ch = self.params[ch]
            result_file_path = self.result_file_pattern.format(image_dir=image_dir, image_title=image_title, channel=ch)
            IJ.log("RSFISHSegmentor: {}: channel {}: saving to {}".format(image_title, ch, result_file_path))
            self.process_channel(imp_ch, result_file_path, params_ch)
            output_filenames.append(result_file_path)
        IJ.log("RSFISHSegmentor: {}: done".format(image_title))

        return output_filenames
        
    def process_channel(self, imp, results_file, params):
        params['results_file'] = [results_file]
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
            

class BatchRunner:
    image_join_headers = ['x', 'y', 't', 'c', 'intensity', 'nucleus_id', 'channel']
    global_join_headers = image_join_headers + ['filename']

    def __init__(self, nuclei_segmentor, dots_segmentor, base_directory, global_join_filename, global_nuclei_filename, image_join_pattern, image_nuclei_pattern):
        self.nuclei_segmentor = nuclei_segmentor
        self.dots_segmentor = dots_segmentor
        self.base_dir = base_directory
        self.global_join_filename = global_join_filename
        self.global_nuclei_filename = global_nuclei_filename
        self.image_join_pattern = image_join_pattern
        self.image_nuclei_pattern = image_nuclei_pattern

    def run(self, file_list):
        global_join_path = os.path.join(self.base_dir, self.global_join_filename)
        global_nuclei_path = os.path.join(self.base_dir, self.global_nuclei_filename)

        with open(global_join_path, 'w') as global_join_fd, open(global_nuclei_path, 'w') as global_nuclei:
            global_join = csv.DictWriter(global_join_fd, fieldnames=self.global_join_headers, extrasaction='ignore' )
            global_join.writeheader()
            global_nuclei.write('[\n')
            self._iterate_file_list(file_list, global_join, global_nuclei)
            global_nuclei.write(']\n')

    def _iterate_file_list(self, file_list, global_join, global_nuclei):
        for file_idx, file_path in enumerate(open(file_list)):
            file_path = file_path.strip()
            image_path = os.path.splitext(file_path)[0] # Used for templating csv file names
            nuclei = self.nuclei_segmentor.get_image_nuclei(file_path)
            dots_filenames = self.dots_segmentor.process_image(file_path)

            image_nuclei_filename = self.image_nuclei_pattern.format(image_path=image_path)
            with open(image_nuclei_filename, 'w') as image_nuclei:
                self._write_nuclei(nuclei, global_nuclei, image_nuclei, file_path, file_idx == 0)

            image_join_output_filename = self.image_join_pattern.format(image_path=image_path)
            with open(image_join_output_filename, 'w') as image_join:
                self._write_join(dots_segmentor.channels, dots_filenames, nuclei, image_join, global_join, file_path)

    def _write_nuclei(self, nuclei, global_nuclei, image_nuclei, file_path, is_first_file):
        image_nuclei.write('[\n')
        for idx, n in enumerate(nuclei):
            if idx == 0:
                image_nuclei.write(json.dumps(n))
            else:
                image_nuclei.write(',' + json.dumps(n))
            n['filename'] = file_path
            if idx == 0 and is_first_file:
                global_nuclei.write(json.dumps(n))
            else:
                global_nuclei.write(',' + json.dumps(n))
        image_nuclei.write(']\n')

    def _write_join(self, channels, filenames, nuclei, image_join, global_join, file_path):
        image_join_output = csv.DictWriter(image_join, extrasaction='ignore', fieldnames=self.image_join_headers)
        image_join_output.writeheader()
        for ch, csv_file in zip(dots_segmentor.channels, filenames):
            csv_out = join.join_from_csv(nuclei, csv_file, dict(channel=ch, filename=file_path))
            image_join_output.writerows(csv_out)
            global_join.writerows(csv_out)


file_list = create_file_list(directory, pattern)
nuclei_segmentor = QuPathSegmentor(nuclei_channel, qupath_executable, tmp_dir, script_dir, params_override=nuclei_params_override)
nuclei_segmentor.process_file_list(file_list)
dots_segmentor = RSFISHSegmentor(channels=dots_channels, params_override=dots_params_override)
batch_runner = BatchRunner(nuclei_segmentor, dots_segmentor, directory, global_join_output_filename, global_nuclei_output_filename, image_join_output_pattern, image_nuclei_output_pattern)
batch_runner.run(file_list)

