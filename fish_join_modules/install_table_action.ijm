macro "Table Action" {
    options = call("ij.Macro.getOptions");
    items = split(options,"|");
    title = items[0];
    start = items[1];
    end = items[2];
    print(Table.getString('filename', start));
}
