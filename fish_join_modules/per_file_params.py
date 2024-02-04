import csv
import os

def typify(value):
    """Convert string to a proper type: int, float or str """
    try:
        return int(value)
    except:
        try:
            return float(value)
        except:
            return value

def _parse_row(row_dict, nuclei_channel, dots_channels):
    filename = row_dict.pop('filename')
    nuclei_params = {}
    dots_params = {}
    for c in dots_channels:
        dots_params[c] = {}

    for col, value in row_dict.items():
       ch_name, param_name = col.split(":", 1)
       try:
           ch_number = int(ch_name.replace("ch", ""))
       except:
           raise ValueError("Can't extract channel number from column name: {}".format(ch_name))
       value = typify(value)
       if value == '':
           # Ignore empty values
           continue
       if ch_number == nuclei_channel:
           nuclei_params[param_name] = value
       elif ch_number in dots_channels:
           dots_params[ch_number][param_name] = value
       else:
           print "WARNING: per-file param file includes column {} for channel {} which is unused by nuclei or dots".format(ch_name, ch_number)

    return filename, nuclei_params, dots_params


def read_per_file_params(filename, base_directory, nuclei_channel, dots_channels):
    nuclei_params, dots_params = {}, {}
    if not filename:
        return nuclei_params, dots_params
    csv_reader = csv.DictReader(open(filename))
    for row in csv_reader:
        filename, row_nuclei_params, row_dots_params = _parse_row(row, nuclei_channel, dots_channels)
        key = os.path.join(base_directory, filename)
        if key in dots_params or key in nuclei_params:
            print "WARNING: per-file param file includes multiple entries for file {}, ignoring duplicate entries".format(key)
            continue
        if row_nuclei_params:
            nuclei_params[key] = row_nuclei_params
        if row_dots_params:
            dots_params[key] = row_dots_params

    return nuclei_params, dots_params
