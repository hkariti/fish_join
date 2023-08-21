import os

from ij import IJ

MODULES_DIR = os.path.dirname(__file__
                              )
def install_macro(macro_name):
    macro_path = os.path.join(MODULES_DIR, macro_name) + '.ijm'
    IJ.run("Install...", "install={}".format(macro_path));
