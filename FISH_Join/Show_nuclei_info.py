#@ File (style="directory") directory

import json

from ij import IJ
from ij.measure import ResultsTable

from fish_join_modules.output_filenames import global_nuclei_filename

def main():
    global_nuclei_path = global_nuclei_filename(str(directory))
    nuclei = json.load(open(global_nuclei_path))
    rt = ResultsTable()
    for n in nuclei:
        IJ.log(repr(n))
        rt.addRow()
        rt.addValue('filename', n['filename'])
        rt.addValue('id', n['id'])
        rt.addValue('centroid_x', n['centroid'][0])
        rt.addValue('centroid_y', n['centroid'][1])
        rt.addValue('area', n['area'])
    rt.show('Nuclei info')

if __name__ in ['__builtin__', '__main__']:
    main()
