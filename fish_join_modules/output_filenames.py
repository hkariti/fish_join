import os

def image_join_filename(image_path):
    no_ext_path = os.path.splitext(image_path)[0]
    return no_ext_path + '_nuclei_dots_joined.csv'

def image_nuclei_filename(image_path):
    no_ext_path = os.path.splitext(image_path)[0]
    return no_ext_path + '_nuclei.json'

def global_join_filename(base_dir):
    return os.path.join(base_dir, 'nuclei_dots_joined.csv')

def global_nuclei_filename(base_dir):
    return os.path.join(base_dir, 'nuclei.json')
