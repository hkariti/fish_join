import csv
import json


def join_data_files(nuclei_json, dots_csv):
    """
    Run join on all dots and nuclei from the given data files
    """
    nuclei = parse_nuclei_geojson(json.load(open(nuclei_json)))
    dots = prepare_dots_csv(csv.DictReader(open(dots_csv)))

    for d in dots:
        d['nuclei_id'] = find_matching_nuclei(nuclei, d)

    return nuclei, dots

def find_matching_nuclei(nuclei, dot):
    """
    Find the matching nuclei for the given dot
    """
    coords = dot['coords']

    for n in nuclei:
        if _is_point_inside_polygon(n['polygon'], coords):
            return n['id']
    return None

def parse_nuclei_geojson(geojson):
    nuclei = []
    index = 0
    for feature in geojson['features']:
        try:
            if feature['properties']['objectType'] != 'cell':
                continue
        except KeyError:
            continue
        try:
            polygon = feature['nucleusGeometry']['coordinates'][0]
            nuclei.append(dict(id=index, polygon=polygon))
        except KeyError, IndexError:
            print("parse_nuclei_geojson: nuclei {} is bad, skipping".format(index))
            continue
        finally:
            index += 1

    return nuclei

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

