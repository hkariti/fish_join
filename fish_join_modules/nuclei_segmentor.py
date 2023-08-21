import shutil
import json
import os
import subprocess

from ij import IJ

SCRIPT_DIR = os.path.dirname(__file__)

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

    def __init__(self, channel, qupath_executable='QuPath', tmp_dir='/tmp', keep_project_dir=False, params_override={}):
        self.channel = channel
        self.qupath_executable = qupath_executable
        self.tmp_dir = tmp_dir
        self._qupath_project_filename = 'project.qpproj'
        self.keep_project_dir = keep_project_dir

        params = self._default_params.copy()
        params.update(params_override)
        params['detectionImage'] = params['detectionImage'].format(channel=channel)
        self.params_json = json.dumps(params)

    def qupath_script(self, script_name, project=None, args=[]):
        script_path = os.path.join(SCRIPT_DIR, script_name)
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
