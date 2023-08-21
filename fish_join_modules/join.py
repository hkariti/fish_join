import csv
import json


def join_from_csv(nuclei, csv_filename, additional_fields={}):
    """
    Join all dots from the given csv with the given list of nuclei.

    Returns a list of dicts, each corresponding to a row in the CSV, with
    additional 'nucleus_id' field. Additional fields will be added from the
    additional_fields parameter.
    """
    dots = prepare_dots_csv(csv.DictReader(open(csv_filename)))

    for d in dots:
        d['nucleus_id'] = find_matching_nuclei(nuclei, d)
        d.update(additional_fields)

    return dots

def find_matching_nuclei(nuclei, dot):
    """
    Find the matching nuclei for the given dot
    """
    coords = dot['coords']

    for n in nuclei:
        if _is_point_inside_polygon(n['polygon'], coords):
            return n['id']
    return None

def prepare_dots_csv(csv_dict):
    """
    Return a list of dicts that's easier to work with. Add a 'coords' key that combines x and y and sort dots by y
    value, to match how nuclei are sorted.
    """
    def add_coords(d):
        d['coords'] = (float(d['x']), float(d['y']))
        return d
    dots = [ add_coords(d) for d in csv_dict ]

    return sorted(dots, key=lambda d: d['coords'][1])

def _is_point_inside_polygon(polygon, point):
    """
    Detect if a dot is inside the given polygon using the Ray Tracing algorithm.

    polygon: iterable of x-y pairs in clockwise or anticlockwise order
    dot: x-y pair

    returns True if dot is inside polygon
    """
    # Thanks ChatGPT!
    n = len(polygon)
    x, y = point

    inside = False
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        if y > min(y1, y2):
            if y <= max(y1, y2):
                if x <= max(x1, x2):
                    if y1 != y2:
                        x_intercept = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                        if x1 == x2 or x <= x_intercept:
                            inside = not inside

    return inside

