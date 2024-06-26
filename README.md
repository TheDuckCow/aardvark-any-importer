# NOTE:

This addon was useful, but is not longer very relevant with Blender 4.1's general drag and drop support - a superior solution we wanted all along!

# Aardvark (Any File) Importer

This is a blender add-on designed to make general file importing easy and fast. By default, when you want to import a file, you must first select the correct exporter. Plus, you can only import one file at a time (typically). This add-on attempts to make it easier to select multiple files and even import different types of files (extensions) at once, so you don't have to think much ahead.

This addon as been updated so that it works with Blender 3.1, and as far back as Blender 2.8.

## How to install?

1) Download the `aardvark_any_importer.py` file [from here](https://raw.githubusercontent.com/TheDuckCow/aardvark-any-importer/master/aardvark_any_importer.py), save it as a file on your machine somewhere.
2) In blender 2.8, go to edit > preferences, click on the add-on tab on the left
3) Press the "Install..." button
4) Select the downloaded `aardvark_any_importer.py` in the filebrowser, press install
5) Be sure to tick the box to enable the add-on! Search for "Aardvark" if it doesn't show up automatically.

## How to set it up?

In add-on preferences (see how to get there above), you can view all the extensions which have an associated exporter. In this view, you can customize which operator to call for each extension type. By default, the built in and available operators will be used (based on what is enabled at the time of the add-on's use).

Want to add another extension, and link to a specific operator? Follow the steps below:

1) In the add-on's preferences, click "Add extension"
2) Input the name of the extension, e.g. "png" (noting that you could start with a period, but it will get auto-removed on confirmation anyways)
3) Get the operator code you want to associate. Easily done by pressing control+copy with the mouse hovering over the operator in the interface/file menu.
4) Paste in the operator code; note if the copied code is for instance "bpy.ops.import_scene.obj()", then the text entered should be written as "import_scene.obj" (ie, remove bpy.ops and the suffix parentheses).


## How to use it?

### 1) Activate it from one of these places:

a) Use the shortcut key: `a` + `control` + `shift`
b) Assign your own shortcut key for the operator `import_any.file`.
c) File > Import > Any file importer
d) Press F4 > Import > Any file importer


### 2) Select your files

The whole point is you get straight to selecting the files before worrying about the file formats. You can select multiple files in a folder with shift-click, b for box select, or press a to select all (subfolders selected will be ignored).

> **_NOTE:_** Only single-file selection is supported so far.

### 3) Decide how to import the selected files

In the filebrowser popup, see the settings at right. There are three modes:

a) Per file: Prompt UI setting popups for each of the selected files
b) Per extension: Prompt UI settings popups once per each extension type of the selected files (**_NOTE:_** Due to only one file importing at a time, this setting does not yet do anything and behaves like Per File above)
c) Use defaults: Use the default import settings for all files, do not popup any settings.

### 4) Press import!

Depending on what you selected in step 3, you either get to sit back and relax, or you get to input the native settings for each importer for the files selected.

Note that if you want to "undo", you will have to press control+z once per each file imported (this is a consequence of the way this was implemented to allow for settings adjustments). Take into consideration before importing a thousand files, maybe save first!

## Have issues or need support?

Please post to the [issues page](https://github.com/TheDuckCow/aardvark-any-importer/issues) on this repository.
