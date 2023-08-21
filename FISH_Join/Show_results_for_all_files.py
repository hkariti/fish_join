#@ File (style="directory") directory

from ij.measure import ResultsTable

from fish_join_modules.output_filenames import global_join_filename

def main():
    global_join_path = global_join_filename(str(directory))
    rt = ResultsTable.open(global_join_path)
    rt.show('All dots and their nuclei')

if __name__ in ['__builtin__', '__main__']:
    main()
