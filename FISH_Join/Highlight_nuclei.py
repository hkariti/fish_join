#@ String (label="Image file (empty for current image)") image
#@ String (label="Nuclei ids, comma separated (-1 for all)") nucleui_ids
#@ Boolean (label="Populate ROI with dots") populate_roi
import json
from ij import IJ, ImagePlus, WindowManager
from ij.gui import Overlay, Roi, PolygonRoi, PointRoi
from ij.plugin.frame import RoiManager
import csv

import fish_join_modules.output_filenames as output_filenames


def annotate(image=None, nucleus_id=None, populate_roi=True):
    """
    Annotate nuclei on the given image.

    :param image: Path to image to open, or None to use the current image.
    :param nucleus_id: Either ID or list of IDs of Nucleui to highlight. To highlight all
                       nuclei, pass None or ID of -1.
    :param populate_roi: Populate ROI with dots for each nucleus
    """
    if not image:
        _imp = WindowManager.getCurrentImage()
        if _imp is None:
            raise ValueError("No image opened")
    else:
        _imp = IJ.openImage(image)
        if _imp is None:
            raise IOError(image)
    image_path = _get_imp_file_path(_imp)
    imp = _imp.duplicate()  # Create a duplicate of the image to prevent modification of the original

    nuclei_path = output_filenames.image_nuclei_filename(image_path)
    nuclei = json.load(open(nuclei_path))
    if nucleus_id is None:
        chosen_nuclei = nuclei
    else:
        if isinstance(nucleus_id, int):
            nucleus_id = [nucleus_id]
        chosen_nuclei = [ n for n in nuclei if n['id'] in nucleus_id or -1 in nucleus_id ]

    overlay = None
    for nucleus in chosen_nuclei:
        overlay = add_polygon_overlay(imp, nucleus['polygon'], nucleus['id'], overlay)

    if populate_roi:
        add_dots_roi(image_path, [n['id'] for n in chosen_nuclei])

def add_polygon_overlay(imp, polygon_edges, label=None, overlay=None):
    """
    Adds a polygon overlay with a label to the specified ImagePlus.
    
    :param imp: The ImagePlus object to which the overlay will be added.
    :param polygon_edges: List of (x, y) coordinates representing the polygon's edges.
    :param label: The label text for the overlay.
    :param overlay: Optional overlay object to use, will be created if None.

    :return: Overlay object
    """
    
    x_points = []
    y_points = []
    for x, y in polygon_edges:
        x_points.append(x)
        y_points.append(y)
    
    polygon_roi = PolygonRoi(x_points, y_points, Roi.POLYGON)
    if label:
        polygon_roi.setName(str(label))
    if overlay is None:
        overlay = Overlay()
        imp.setOverlay(overlay)
        imp.show()
        
    overlay.add(polygon_roi)

    return overlay
    
def add_dots_roi(image_path, chosen_nuclei):
    """
    Add the dots inside the given nuclei to the current image's ROI

    :param image_path: Path to current image, used to find the dots-nuclei CSV file
    :param chosen_nuclei: List of nuclei IDs
    """
    # Get the RoiManager instance
    roi_manager = RoiManager.getInstance()

    # If RoiManager is not open, create a new instance
    if roi_manager is None:
        roi_manager = RoiManager()
        roi_manager.setVisible(True)
    dots_path = output_filenames.image_join_filename(image_path)
    with open(dots_path, 'rb') as dots:
        for dot in csv.DictReader(dots):
            try:
                n = int(dot['nucleus_id'])
            except ValueError:
                # We don't care about dots that don't fit to any nucleus
                continue
            if n in chosen_nuclei:
                x = float(dot['x'])
                y = float(dot['y'])
                c = int(dot['channel'])
                roi = PointRoi(x, y)
                roi.setName('{x}_{y}_{c}_{n}'.format(x=x, y=y, c=c, n=n))
                roi_manager.addRoi(roi)

def _get_imp_file_path(imp):
    file_info = imp.getOriginalFileInfo()

    if file_info:
        if file_info.url:
            return file_info.url.replace('file:', '')
        else:
            return file_info.filePath
    raise ValueError("No file backing this image")

if __name__ in ['__builtin__', '__main__']:
    nuclei_ids_ints = [ int(x) for x in nucleui_ids.split(',') ]
    annotate(image, nuclei_ids_ints, populate_roi=populate_roi)
