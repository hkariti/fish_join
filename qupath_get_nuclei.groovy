import static qupath.lib.gui.scripting.QPEx.*

if (args.size() > 0)
    qupath_params = args[0]
else {
    println("Expected args: JSON_OF_PARAMS")
    return
}

getProject().getImageList().each { img ->
    def imgPath = img.readImageData().getServer().getURIs()[0].getPath()
    def targetGeo = imgPath.take(imgPath.lastIndexOf('.')) + '_nuclei.geojson'
    setImageType('FLUORESCENCE');
    createFullImageAnnotation(true)
    runPlugin('qupath.imagej.detect.cells.WatershedCellDetection', qupath_params)
    selectDetections()
    exportSelectedObjectsToGeoJson(targetGeo, "FEATURE_COLLECTION")
 }
