import json
from ij import IJ, ImagePlus, WindowManager
from ij.gui import Overlay, Roi, PolygonRoi

import fish_join_modules.output_filenames as output_filenames


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
    
def annotate(image=None, nucleus_id=None):
    """
    Annotate nuclei on the given image.

    :param image: Path to image to open, or None to use the current image.
    :param nucleus_id: Nucleus ID to highlight or None to highlight all nuclei.
    """
    if image is None:
        _imp = WindowManager.getCurrentImage()
        if _imp is None:
            raise ValueError("No image opened")
    else:
        _imp = IJ.openImage(image)
    image_path = _get_imp_file_path(_imp)
    imp = _imp.duplicate()  # Create a duplicate of the image to prevent modification of the original

    nuclei_path = output_filenames.image_nuclei_filename(image_path)
    nuclei = json.load(open(nuclei_path))
    if nucleus_id is None:
        chosen_nuclei = nuclei
    else:
        if isinstance(nucleus_id, int):
            nucleus_id = [nucleus_id]
        chosen_nuclei = [ n for n in nuclei if n['id'] in nucleus_id ]

    overlay = None
    for nucleus in chosen_nuclei:
        overlay = add_polygon_overlay(imp, nucleus['polygon'], nucleus['id'], overlay)

def _get_imp_file_path(imp):
    file_info = imp.getOriginalFileInfo()

    if file_info:
        return file_info.url.replace('file:', '')
    raise ValueError("No file backing this image")
