#@ File (label="Images directorory",style="directory") _directory
#@ String (label="Filename pattern") pattern
#@ Boolean (label="Reuse existing file list",value=True) reuse_file_list
#@ Boolean (label="Segment nuclei",value=True) do_nuclei_segmentation
#@ Integer (label="Nucleus channel") nuclei_channel
#@ String (label="Nuclei segmentation params",value="{}") _nuclei_params_override
#@ String (label="QuPath executable") qupath_executable
#@ Boolean (label="Segment dots",value=True) do_dots_segmentation
#@ String (label="Dots channels (comma separated)") _dots_channel
#@ String (label="Dots segmentation params (key per channel)",value="{}") _dots_params_override
#@ Boolean (label="Show results table when finished",value=True) show_results_table
import os
import csv
import json
from glob import fnmatch
import tempfile
import itertools

from ij import IJ

import fish_join_modules.join as join
from fish_join_modules.nuclei_segmentor import QuPathSegmentor
from fish_join_modules.dots_segmentor import RSFISHSegmentor
from fish_join_modules.output_filenames import global_join_filename, global_nuclei_filename, \
        image_join_filename, image_nuclei_filename


tmp_dir = tempfile.gettempdir()
directory = str(_directory)
if _nuclei_params_override.strip():
    nuclei_params_override = json.loads(_nuclei_params_override)
else:
    nuclei_params_override = {}
dots_channels = [ int(x.strip()) for x in _dots_channel.split(',') ]
if _dots_params_override.strip():
    dots_params_override = json.loads(_dots_params_override)
else:
    dots_params_override = {}


def create_file_list(directory, pattern, reuse=False):
    file_list_path = os.path.join(directory, 'fish_join_file_list')
    if reuse and os.path.exists(file_list_path):
        return file_list_path
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
        global_join_path = global_join_filename(self.base_dir)
        global_nuclei_path = global_nuclei_filename(self.base_dir)

        IJ.log("Starting dots processing")
        with open(global_join_path, 'wb') as global_join_fd, open(global_nuclei_path, 'w') as global_nuclei:
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

            with open(image_join_filename(file_path), 'wb') as image_join:
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

    def _write_join(self, channels, filenames, nuclei, image_join, global_join, file_path, sort=True):
        image_join_output = csv.DictWriter(image_join, extrasaction='ignore', fieldnames=self.image_join_headers)
        csv_out = []
        for ch, csv_file in zip(self.dots_segmentor.channels, filenames):
            new_csv = join.join_from_csv(nuclei, csv_file, dict(channel=ch, filename=file_path))
            csv_out.append(new_csv)
        csv_out = itertools.chain.from_iterable(csv_out)

        if sort:
            # null nucleus check is used to put all null nuclei at the bottom
            csv_out = sorted(csv_out, key=lambda d: (d['nucleus_id'] is None, d['nucleus_id'], d['channel']))
        image_join_output.writeheader()
        image_join_output.writerows(csv_out)
        global_join.writerows(csv_out)


def main():
    file_list = create_file_list(directory, pattern, reuse_file_list)
    nuclei_segmentor = QuPathSegmentor(nuclei_channel, qupath_executable, tmp_dir, params_override=nuclei_params_override)
    if do_nuclei_segmentation:
        nuclei_segmentor.process_file_list(file_list)
    dots_segmentor = RSFISHSegmentor(channels=dots_channels, params_override=dots_params_override)
    batch_runner = BatchRunner(nuclei_segmentor, dots_segmentor, directory)
    if do_dots_segmentation:
        batch_runner.run(file_list)
    if show_results_table:
        IJ.run("Show results for all files", "directory="+directory)


if __name__ in ['__builtin__','__main__']:
    main()
