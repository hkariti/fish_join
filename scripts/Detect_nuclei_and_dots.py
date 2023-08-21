import os
import csv
import json
from glob import fnmatch

from ij import IJ
from ij.measure import ResultsTable

import fish_join_modules.join as join
from fish_join_modules.nuclei_segmentor import QuPathSegmentor
from fish_join_modules.dots_segmentor import RSFISHSegmentor
from fish_join_modules.output_filenames import global_join_filename, global_nuclei_filename, \
        image_join_filename, image_nuclei_filename

tmp_dir = os.environ['TMPDIR']
directory = "/Users/hkariti/repo/technion/fish_join/data_files"
pattern = "*_MAX.tif"
nuclei_params_override = json.loads('{}')
nuclei_channel = 4
dots_channels = [1,2,3]
dots_params_override = json.loads('{}')
qupath_executable = '/Applications/QuPath.app/Contents/MacOS/QuPath'
script_dir = '/Users/hkariti/repo/technion/fish_join/fish_join_modules/'
show_results_table = True


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


class BatchRunner:
    image_join_headers = ['x', 'y', 't', 'c', 'intensity', 'nucleus_id', 'channel']
    global_join_headers = image_join_headers + ['filename']

    def __init__(self, nuclei_segmentor, dots_segmentor, base_directory):
        self.nuclei_segmentor = nuclei_segmentor
        self.dots_segmentor = dots_segmentor
        self.base_dir = base_directory

    def run(self, file_list):
        global_join_path = os.path.join(self.base_dir, global_join_filename)
        global_nuclei_path = os.path.join(self.base_dir, global_nuclei_filename)

        IJ.log("Starting dots processing")
        with open(global_join_path, 'w') as global_join_fd, open(global_nuclei_path, 'w') as global_nuclei:
            global_join = csv.DictWriter(global_join_fd, fieldnames=self.global_join_headers, extrasaction='ignore' )
            global_join.writeheader()
            global_nuclei.write('[\n')
            self._iterate_file_list(file_list, global_join, global_nuclei)
            global_nuclei.write(']\n')
        IJ.log("Finished processing all files")

    def _iterate_file_list(self, file_list, global_join, global_nuclei):
        for file_idx, file_path in enumerate(open(file_list)):
            file_path = file_path.strip()
            nuclei = self.nuclei_segmentor.get_image_nuclei(file_path)
            dots_filenames = self.dots_segmentor.process_image(file_path)

            with open(image_nuclei_filename(file_path), 'w') as image_nuclei:
                self._write_nuclei(nuclei, global_nuclei, image_nuclei, file_path, file_idx == 0)

            with open(image_join_filename(file_path), 'w') as image_join:
                self._write_join(self.dots_segmentor.channels, dots_filenames, nuclei, image_join, global_join, file_path)

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
        for ch, csv_file in zip(self.dots_segmentor.channels, filenames):
            csv_out = join.join_from_csv(nuclei, csv_file, dict(channel=ch, filename=file_path))
            image_join_output.writerows(csv_out)
            global_join.writerows(csv_out)




def main():
    file_list = create_file_list(directory, pattern)
    nuclei_segmentor = QuPathSegmentor(nuclei_channel, qupath_executable, tmp_dir, script_dir, params_override=nuclei_params_override)
    nuclei_segmentor.process_file_list(file_list)
    dots_segmentor = RSFISHSegmentor(channels=dots_channels, params_override=dots_params_override)
    batch_runner = BatchRunner(nuclei_segmentor, dots_segmentor, directory)
    batch_runner.run(file_list)
    if show_results_table:
        global_join_path = global_join_filename(directory)
        rt = ResultsTable.open(global_join_path)
        rt.show('All dots and their nuclei')


if __name__ in ['__builtin__','__main__']:
    main()
