import static qupath.lib.gui.scripting.QPEx.*
import org.json.JSONObject

if (args.size() > 1) {
    global_qupath_params_json = args[0]
    per_file_params_json = args[1]
} else if (args.size() == 1) {
    global_qupath_params_json = args[0]
    per_file_params_json = "{}"
} else {
    println("Expected args: JSON_OF_PARAMS [JSON_OF_PER_FILE_PARAMS]")
    return
}

def jsonObjectToMap(JSONObject jsonObject) {
    def resultMap = [:]
    jsonObject.keys().each { key ->
        resultMap[key] = jsonObject.get(key)
    }
    return resultMap
}

def per_file_params = jsonObjectToMap(new JSONObject(per_file_params_json))
def global_qupath_params = jsonObjectToMap(new JSONObject(global_qupath_params_json))

def imgPath = getCurrentImageData().getServer().getURIs()[0].getPath()
def targetGeo = imgPath.take(imgPath.lastIndexOf('.')) + '_nuclei.geojson'
setImageType('FLUORESCENCE');
createFullImageAnnotation(true)
def param_overrides = jsonObjectToMap(per_file_params.get(imgPath, new JSONObject("{}")))
def qupath_params = global_qupath_params + param_overrides
def qupath_params_json = (new JSONObject(qupath_params)).toString()
println("QuPathSegmentor: Running on image ${imgPath} with these params: ${qupath_params_json}")
runPlugin('qupath.imagej.detect.cells.WatershedCellDetection', qupath_params_json)
selectDetections()
exportSelectedObjectsToGeoJson(targetGeo, "FEATURE_COLLECTION")
