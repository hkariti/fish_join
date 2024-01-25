import shutil
import json
import os
import subprocess

from ij import IJ

SCRIPT_DIR = os.path.dirname(__file__)

class QuPathSegmentor:
    """
    Segment nuclei using QuPath on a list of image files
    """
    _default_params_microns = {"detectionImage": "Channel {channel}",
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

    _default_params_pixels = {"detectionImage": "Channel {channel}",
                       "backgroundRadius": 0.0,
                       "backgroundByReconstruction": True,
                       "medianRadius": 0.0,
                       "sigma": 150,
                       "minArea": 10000.0,
                       "maxArea": 80000.0,
                       "threshold": 150.0,
                       "watershedPostProcess": True,
                       "cellExpansion": 5.0,
                       "includeNuclei": True,
                       "smoothBoundaries": True,
                       "makeMeasurements": True }

    def __init__(self, channel, qupath_executable='QuPath', tmp_dir='/tmp', keep_project_dir=False, units='microns', params_override={}):
        """
        :param int channel: Image channel that contains nuclei information
        :param str qupath_executable: Location of the QuPath command
        :param str tmp_dir: Directory to create the QuPath project and other temporary files in
        :param bool keep_project_dir: Whether to keep the project dir after run is finished or delete it
        :param str units: Which units the params have. Can be microns or pixels.
        :param dict params_override: Dictionary of parameters overrides to QuPath. See also default_params()
        """
        self.channel = channel
        self.qupath_executable = qupath_executable
        self.tmp_dir = tmp_dir
        self._qupath_project_filename = 'project.qpproj'
        self.keep_project_dir = keep_project_dir

        if units == 'microns':
            params = self._default_params_microns.copy()
        elif units == 'pixels':
            params = self._default_params_pixels.copy()
        else:
            raise ValueError("units must be pixels or microns. Got: {}".format(units))

        params.update(params_override)
        params['detectionImage'] = params['detectionImage'].format(channel=channel)
        self.params_json = json.dumps(params)

    def qupath_script(self, script_name, project=None, args=[]):
        """
        Run a QuPath script

        :param str script_name: Name of script file. Scripts are assumed to be in the directory containing this module.
        :param str project: Optional path to QuPath project directory or project file
        :param list args: List of parameters to pass to the script
        """
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

    def process_file_list(self, file_list_path, per_file_params={}):
        """
        Run QuPath on a list of files.

        Raw results will be written to a geojson file according to the format {image_path}_nuclei.geojson. 
        Use get_image_nuclei() to parse these files.

        :param str file_list_path: Path to a list of files, one path per line
        :param dict per_file_params: Per-file param overrides
        """
        qupath_project = os.path.join(self.tmp_dir, 'qupath')
        IJ.log("QuPathSegmentor: creating QuPath project")
        self.qupath_script('qupath_create_project.groovy', args=[file_list_path, qupath_project])
        IJ.log("QuPathSegmentor: detecting nuclei")
        per_file_params_json = json.dumps(per_file_params)
        self.qupath_script( 'qupath_get_nuclei.groovy', args=[self.params_json, per_file_params_json], project=qupath_project)
        if not self.keep_project_dir:
            IJ.log("QuPathSegmentor: cleaning up QuPath project")
            shutil.rmtree(qupath_project)
        IJ.log("QuPathSegmentor: done")

    def get_image_nuclei(self, image_path):
        """
        Return a list of nuclei in the image. Each nucleus object has
        an ID and a list of polygon edges. Data comes from the image's
        geojson file created using process_file_list()

        :param str image_path: Path to image
        :return list[dict]: List of Nucleus dictionaries
        """
        nuclei_file = self._get_output_filename(image_path)

        return self._parse_nuclei_geojson(nuclei_file)

    def default_params(self):
        """
        Return default QuPath parameters. Mostly useful for reference of available parameters.
        """
        return self._default_params

    def _parse_nuclei_geojson(self, geojson):
        """
        Parse QuPath's geojson file and return a list of dicts with
        each nucleus' ID and polygon vertices.

        :param geojson: either a path to a filename, an open geojson file
                        or a parsed geojson as a dict object.
        :return list[dicts]:
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
                centroid = calc_centroid(polygon)
                area = feature["properties"]['measurements']['Nucleus: Area']
                nuclei.append(dict(id=index, polygon=polygon,
                                   centroid=centroid, area=area))
            except (KeyError, IndexError):
                IJ.log("parse_nuclei_geojson: nuclei {} is bad, skipping".format(index))
                continue
            finally:
                index += 1

        return nuclei

    def _get_output_filename(self, image_file_path):
        filename = os.path.splitext(image_file_path)[0]

        return filename + '_nuclei.geojson'

def calc_centroid(vertices):
    x, y = 0, 0
    n = len(vertices)
    signed_area = 0
    for i in range(len(vertices)):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        # shoelace formula
        area = (x0 * y1) - (x1 * y0)
        signed_area += area
        x += (x0 + x1) * area
        y += (y0 + y1) * area
    signed_area *= 0.5
    x /= 6 * signed_area
    y /= 6 * signed_area
    return x, y
