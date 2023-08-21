macro "Table Action" {
    options = call("ij.Macro.getOptions");
    items = split(options,"|");
    title = items[0];
    start = items[1];
    end = items[2];
    filename = Table.getString('filename', start)
    nucleus_id = Table.get('nucleus_id', start)
    if (isNaN(nucleus_id)) {
        nucleus_id = -2;
    }
    run("Highlight nuclei", "image=" + filename + " nucleus_id=" + nucleus_id);
}
