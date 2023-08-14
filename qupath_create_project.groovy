import groovy.io.FileType
import java.awt.image.BufferedImage
import qupath.lib.images.servers.ImageServerProvider
import qupath.lib.gui.commands.ProjectCommands

//Did we receive a string via the command line args keyword?
if (args.size() > 0)
    imageList = new File(args[0])
else
    imageList = Dialogs.promptForFile("Select file with image list", null, null, null)

if (imageList == null)
    return
    
//Check if we already have a QuPath Project directory in there...
projectName = "fish_join_qupath"
File directory = new File(projectName)

if (!directory.exists())
{
    print("No project directory, creating one!")
    directory.mkdirs()
}

// Create project
def project = Projects.createProject(directory , BufferedImage.class)

// Add files to the project
imageList.eachLine { file ->
    def imagePath = file
    // Get serverBuilder
    def support = ImageServerProvider.getPreferredUriImageSupport(BufferedImage.class, imagePath)
    def builder = support.builders.get(0)
    // Make sure we don't have null 
    if (builder == null) {
       print "Image not supported: " + imagePath
       return
    }
    // Add the image as entry to the project
    print "Adding: " + imagePath
    entry = project.addImage(builder)

    // Add an entry name (the filename)
    entry.setImageName(imagePath)
 }

// Changes should now be reflected in the project directory
project.syncChanges()
