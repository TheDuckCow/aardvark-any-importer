# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""
Goals of addon:
- Provide a general importer experience for multiple files
- Support drag and drop selections (from the same folder)
- Provide a way to customize settings used for each style of importer

Approach: Avoid code duplication or UI rewriting where possible. Use default
invocation methods if possible. To do this, we will create a "queue" of imports
which get triggered subsequently as prior imports complete. This will also keep
the addon mostly stable, though does mean undo/redo would count as multiple
steps.

In user preferences, the user specifies which operator to use with which
filetype. Good defaults will be provided, based on those built into blender.

"""


bl_info = {
	"name": "Aardvark Any Importer",
	"category": "Import-Export",
	"version": (1, 0, 1),
	"blender": (2, 80, 0),
	"location": "File > Import > Any file importer",
	"description": "General purpose, multi file, multi extension importer",
	"wiki_url": "",
	"author": "Patrick W. Crawford <support@theduckcow.com>",
	"tracker_url":"https://github.com/TheDuckCow/aardvark-any-importer"
}

import importlib
import os

import bpy
from bpy_extras.io_utils import ImportHelper

# Cache of bl_idname's and true/false availability to avoid slow UI drawing
oper_cache = {}

# queue of file (keys) to be imported (value: success bool)
import_queue = {}


def get_user_preferences(context=None):
	"""Intermediate method for pre and post blender 2.8 grabbing preferences"""
	if not context:
		context = bpy.context
	prefs = None
	if hasattr(context, "user_preferences"): # 2.7
		prefs = context.user_preferences.addons.get(__name__, None)
	elif hasattr(context, "preferences"): # 2.8
		prefs = context.preferences.addons.get(__name__, None)
	if prefs:
		return prefs.preferences
	return None


def make_annotations(cls):
	"""Add annotation attribute to class fields to avoid 2.8 warnings"""
	if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
		return cls
	bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}
	if bl_props:
		if '__annotations__' not in cls.__dict__:
			setattr(cls, '__annotations__', {})
		annotations = cls.__dict__['__annotations__']
		for k, v in bl_props.items():
			annotations[k] = v
			delattr(cls, k)
	return cls


def layout_split(layout, factor=0.0, align=False):
	"""Intermediate method for pre and post blender 2.8 split UI function"""
	if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
		return layout.split(percentage=factor, align=align)
	return layout.split(factor=factor, align=align)


def reset_oper_cache():
	"""Way to reset cache of operator availabilty, to avoid stale pref draw"""
	global oper_cache
	oper_cache = {}


def operator_exists(ref, refresh=True):
	"""Returns true if the operator is available for use.

	Sample input: import_scene.obj
	"""
	global oper_cache
	if refresh:
		oper_cache = {}
	if refresh is False and ref in oper_cache:
		return oper_cache[ref]
	if "." not in ref:
		return False
	base, oprs = ref.split(".")
	res = base in dir(bpy.ops) and oprs in dir(getattr(bpy.ops, base))
	oper_cache[ref] = res
	return res


class IMPORT_OT_import_any_file(bpy.types.Operator, ImportHelper):
	"""General purpose, multi file, multi extension importer"""
	bl_idname = "import_any.file"
	bl_label = "Any-file importer"
	bl_options = {'REGISTER', 'UNDO'}

	files = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
	filter_glob = bpy.props.StringProperty(
		default="*",  # should be overwritten based on prefs
		options={'HIDDEN'})

	setting_mode = bpy.props.EnumProperty(
		name = "Show settings",
		items = (
			("file", "Per File", "Pop up settings per selected file"),
			("extension", "Per Extension", "Pop up settings per extension type"),
			("defaults", "Use defaults", "Use defaults for all importers"),
			)
		)

	directory = ''

	def execute(self, context):
		prefs = get_user_preferences(context)

		# If no extensions set, just reset to apply defaults
		if not prefs.file_extensions:
			bpy.ops.import_any.reset_extensions()
		curr_exts = [ext.extension for ext in prefs.file_extensions]

		print("Select files:")
		self.directory = os.path.dirname(self.filepath)
		print("Folder:", self.directory)
		print(self.files)
		print(self.files[0])
		print(dir(self.files[0]))

		extensions = [os.path.splitext(imp.name)[-1][1:] for imp in self.files]
		extensions = set(extensions)

		ext_missing = []
		for ext in extensions:
			if ext not in curr_exts:
				ext_missing.append(ext)
				continue
			self.import_single(context, ext)

		if ext_missing:
			self.report({"WARNING"},
				"Extensions not associated: "+", ".join(ext_missing))
		print("Finished")
		return {'FINISHED'}

	def import_single(self, context, ext):
		"""Import all files of a single extension type"""
		files = [imp.name for imp in self.files if imp.name.endswith(ext)]
		print("About to import files:")
		print(files)

		prefs = get_user_preferences(context)
		oper = None
		for pref_set in prefs.file_extensions:
			if pref_set.extension != ext:
				continue
			oper = pref_set.operator
			break

		print("Operator found: "+str(oper))

		# need to get the inputs required
		props = context.window_manager.operator_properties_last(oper)
		print("Properties: ", dir(props))
		kwargs = {}
		args = ['INVOKE_DEFAULT']

		# capture as many scenarios as possible, won't be perfect
		bfilepath = hasattr(props, "filepath")
		bdirectory = hasattr(props, "directory")
		bfiles = hasattr(props, "files")

		if bfilepath and bdirectory and bfiles:
			# Example: bpy.ops.import_mesh.stl
			kwargs["filepath"] = os.path.join(self.directory, files[0])
			kwargs["directory"] = self.directory
			# Yes, this structure is right based on examples like above
			kwargs["files"] = [{"name": name, "name": name} for name in files]
		elif bfilepath and bdirectory and not bfiles:
			# Example: import_scene.fbx
			kwargs["filepath"] = files[0]
			kwargs["directory"] = self.directory
		elif bfilepath and not bdirectory:
			# Example: import_scene.obj
			kwargs["filepath"] = os.path.join(self.directory, files[0])
		elif bfiles and bdirectory:
			# example: import_image.to_plane
			kwargs["files"] = [{"name": name, "name": name} for name in files]
			kwargs["directory"] = self.directory

		# other scenarios, like file, directory,
		print("Apply these args:", args)
		print("Apply these kwargs:", kwargs)

		# Apply to the operator itself, and call
		base, oprs = oper.split(".")
		oper_func = getattr(getattr(bpy.ops, base), oprs)
		print("Function:", oper_func)
		oper_func(*args, **kwargs) # pass both invoke and parameter values
		print("Does the above line block?")
		# do some kwargs magic to input the rig


def get_prefs_extensions(context):
	"""Return a comma separated list of the include extensions"""
	prefs = get_user_preferences(context)
	return ";".join(["*"+pset.extension for pset in prefs.file_extensions])


def import_draw_append(self, context):
	opr = self.layout.operator(
		"import_any.file", text="Any file importer", icon="IMPORT")
	opr.filter_glob = get_prefs_extensions(context)


class IMPORT_OT_import_any_reset_extensions(bpy.types.Operator):
	"""Add an extension to provide an operator association"""
	bl_idname = "import_any.reset_extensions"
	bl_label = "Reset to defaults"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		reset_oper_cache()

		prefs = get_user_preferences(context)
		prefs.file_extensions.clear()

		defaults = {
			# confirmed working
			"bvh": "import_anim.bvh",
			"fbx": "import_scene.fbx",
			"obj": "import_scene.obj",

			# should work
			"abc": "wm.alembic_import",
			"dae": "wm.collada_import",
			"stl": "import_mesh.stl",
			"svg": "import_curve.svg",
			"dxf": "import_scene.dxf",
			"ase": "import_ase.read",
			"mdd": "import_shape.mdd",
			"chan": "import_scene.import_chan",
			"wrl": "import_scene.x3d",
			"x3d": "import_scene.x3d",
			"xyz": "import_mesh.xyz", # also implements .pdb?
			"txt": "text.open",
			"rtf": "text.open",
			"py": "text.open",

			# Implement special case, where defaults to e.g. scene or collections
			# "blend": "wm.append"

			# NOT working
			# "jpg": "import_image.to_plane",
			# "jpeg": "import_image.to_plane",
			# "png": "import_image.to_plane",

			# Probably not working
			# "ply": "import_mesh.ply"
			# "glb": "import_scene.gltf"
			# "gltf": "import_scene.gltf"
		}

		for ext in sorted(defaults):
			# Opt to set up, even if not currently available
			# if not operator_exists(defaults[ext]):
			# 	continue
			new = prefs.file_extensions.add()
			new.extension = ext
			new.operator = defaults[ext]
		return {'FINISHED'}


class IMPORT_OT_import_any_add_extension(bpy.types.Operator):
	"""Add an extension to provide an operator association"""
	bl_idname = "import_any.add_extension"
	bl_label = "Add extension"
	bl_options = {'REGISTER', 'UNDO'}

	extension = bpy.props.StringProperty(name="Extension", default="")

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def execute(self, context):
		reset_oper_cache()

		this_ext = self.extension.replace(".", "").lower()
		prefs = get_user_preferences(context)
		curr_exts = [ext.extension for ext in prefs.file_extensions]
		if this_ext in curr_exts:
			self.report({"ERROR"}, "Extension already defined")
			return {'CANCELLED'}

		itm = prefs.file_extensions.add()
		itm.extension = this_ext
		itm.operator = ""
		return {'FINISHED'}


class IMPORT_OT_import_any_remove_extension(bpy.types.Operator):
	"""Remove an extension from preferences"""
	bl_idname = "import_any.remove_extension"
	bl_label = "Add extension"
	bl_options = {'REGISTER', 'UNDO'}

	extension = bpy.props.StringProperty(name="Extension", default="")

	def execute(self, context):
		reset_oper_cache()

		prefs = get_user_preferences(context)
		pop = None
		for i, ext in enumerate(prefs.file_extensions):
			if ext.extension != self.extension:
				continue
			pop = i
			break
		if pop is not None:
			print("Removing extension association:" + self.extension)
			prefs.file_extensions.remove(pop)
			return {'FINISHED'}
		else:
			self.report({"ERROR"},
				"Extension {} missing, cannot remove".format(self.extension))
			return {'CANCELLED'}


def operator_code_update(self, context):
	"""Auto-fix the input operator value for convenience.

	Goal is to go from bpy.ops.import_scene.obj() to import_scene.obj
	"""
	truncate_suffix = self.operator.endswith("()")
	new_base = None
	if len(self.operator.split("."))==4:
		new_base = ".".join(self.operator.split(".")[2:])

	if new_base and truncate_suffix:
		self.operator = new_base[:-2]
	elif new_base:
		self.operator = new_base
	elif truncate_suffix:
		self.operator = self.operator[:-2]


class FileAssociation(bpy.types.PropertyGroup):
	"""Container for default operators to use with file extensions"""
	extension = bpy.props.StringProperty(
		name="Extension", description="Extension to assign, in format png")
	operator = bpy.props.StringProperty(
		name="Operator", update=operator_code_update,
		description="Operator to use, in format: abc.xyz")


class AardvarkImporterPreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	file_extensions = bpy.props.CollectionProperty(type=FileAssociation)

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		col = row.column()
		col.scale_y = 0.8
		col.label(text="Assign importers to use with extensions.")
		col.label(text="For each extension, input the operator name (similar "
			"to how shortcut keys are defined).")

		col = layout.column(align=True)
		row = col.row()
		row.operator("import_any.add_extension", text="Add extension")
		row.label(text="")
		row.operator("import_any.reset_extensions")
		row.label(text="")
		row.label(text="")
		if not self.file_extensions:
			row = col.row()
			row.label(text="No extension associations, add one below")
		for ext in self.file_extensions:
			row = col.row()
			# row.label(text=ext.extension+":")
			spl = layout_split(row, 0.5)
			spl_col = spl.split()
			spl_col.prop(ext, "operator", text=ext.extension)
			spl_col = spl.split()
			spl_row = spl_col.row()
			skip = False
			ops = spl_row.operator(
				"import_any.remove_extension", text="", icon="X")
			ops.extension = ext.extension
			if not ext.operator:
				spl_row.label(text="Add operator!", icon="ERROR")
				skip = True
			elif "." not in ext.operator:
				spl_row.label(text="Operator should contain '.'", icon="ERROR")
				skip = True
			elif len(ext.operator.split("."))>2:
				spl_row.label(
					text="Operator should only have one '.'", icon="ERROR")
				skip = True

			if not skip:
				if operator_exists(ext.operator, refresh=False):
					spl_row.label(text="", icon="BLANK1")
				else:
					spl_row.label(text="Operator not found (enable addon?)",
						icon="ERROR")


classes = (
	FileAssociation,
	AardvarkImporterPreferences,
	IMPORT_OT_import_any_file,
	IMPORT_OT_import_any_reset_extensions,
	IMPORT_OT_import_any_add_extension,
	IMPORT_OT_import_any_remove_extension,
)


def register():
	for cls in classes:
		make_annotations(cls)
		bpy.utils.register_class(cls)
	bpy.types.TOPBAR_MT_file_import.prepend(import_draw_append)

	reset_oper_cache()


def unregister():
	bpy.types.TOPBAR_MT_file_import.remove(import_draw_append)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	register()
