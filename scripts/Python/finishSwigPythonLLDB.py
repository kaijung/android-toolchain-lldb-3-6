""" Python SWIG post process script for each language

	--------------------------------------------------------------------------
	File: 			finishSwigPythonLLDB.py

	Overview: 		Python script(s) to post process SWIG Python C++ Script 
					Bridge wrapper code on the Windows/LINUX/OSX platform.    
					The Python scripts are equivalent to the shell script (.sh)  
					files.
					For the Python script interpreter (external to liblldb) to 
					be able to import and use the lldb module, there must be 
					two files, lldb.py and _lldb.so, that it can find. lldb.py 
					is generated by SWIG at the same time it generates the C++ 
					file.  _lldb.so is actually a symlink file that points to 
					the LLDB shared library/framework.
					The Python script interpreter needs to be able to 
					automatically find these two files. On Darwin systems it 
					searches in the LLDB.framework, as well as in all the normal 
					Python search paths.  On non-Darwin systems these files will 
					need to be put some place where Python will find them.
					This shell script creates the _lldb.so symlink in the 
					appropriate place, and copies the lldb.py (and 
					embedded_interpreter.py) file to the correct directory.
				
	Environment:	OS:			Windows Vista or newer, LINUX, OSX.
					IDE: 	    Visual Studio 2013 Plugin Python Tools (PTVS)
					Script:		Python 2.6/2.7.5 x64 
					Other:		None.

	Gotchas:		Python debug complied pythonXX_d.lib is required for SWIG
					to build correct LLDBWrapperPython.cpp in order for Visual
					Studio to compile successfully. The release version of the 
					Python lib will not work (20/12/2013). 
					LLDB (dir) CMakeLists.txt uses windows environmental
					variables $PYTHON_INCLUDE and $PYTHON_LIB to locate
					Python files required for the build.

	Copyright:		None.
	--------------------------------------------------------------------------
	
"""

# Python modules:
import os			# Provide directory and file handling, determine OS information
import sys			# System specific parameters and functions
import errno		# OS error results
import shutil		# High-level operations on files and collections of files
import subprocess 	# Call external programs
import ctypes		# Invoke Windows API for creating symlinks

# Third party modules:

# In-house modules:
import utilsOsType		# Determine the OS type this script is running on
import utilsDebug 		# Debug Python scripts

# User facing text:
strMsgOsVersion = "The current OS is %s";
strMsgPyVersion = "The Python version is %d.%d";
strErrMsgProgFail = "Program failure: ";
strErrMsgLLDBPyFileNotNotFound = "Unable to locate lldb.py at path '%s'";
strMsgCopyLLDBPy = "Copying lldb.py from '%s' to '%s'";
strErrMsgFrameWkPyDirNotExist = "Unable to find the LLDB.framework directory '%s'";
strMsgCreatePyPkgCopyPkgFile = "create_py_pkg: Copied file '%s' to folder '%s'";
strMsgCreatePyPkgInitFile = "create_py_pkg: Creating pakage init file '%s'";
strMsgCreatePyPkgMkDir = "create_py_pkg: Created folder '%s'";
strMsgConfigBuildDir = "Configuration build directory located at '%s'";
strMsgFoundLldbFrameWkDir = "Found '%s'";
strMsgPyFileLocatedHere = "Python file will be put in '%s'";
strMsgFrameWkPyExists = "Python output folder '%s' already exists";
strMsgFrameWkPyMkDir = "Python output folder '%s' will be created";
strErrMsgCreateFrmWkPyDirFailed = "Unable to create directory '%s' error: %s";
strMsglldbsoExists = "Symlink '%s' already exists";
strMsglldbsoMk = "Creating symlink for _lldb.so  (%s -> %s)";
strErrMsgCpLldbpy = "copying lldb to lldb package directory";
strErrMsgCreatePyPkgMissingSlash = "Parameter 3 fn create_py_pkg() missing slash"; 
strErrMsgMkLinkExecute = "Command mklink failed: %s";
strErrMsgMakeSymlink = "creating symbolic link";
strErrMsgUnexpected = "Unexpected error: %s";
	
#++---------------------------------------------------------------------------
# Details:	Copy files needed by lldb/macosx/heap.py to build libheap.dylib.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
# Returns:	Bool - True = function success, False = failure.
#			Str - Error description on task failure.
# Throws:	None.
#--
def macosx_copy_file_for_heap( vDictArgs, vstrFrameworkPythonDir ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script macosx_copy_file_for_heap()" );
	bOk = True;
	strMsg = "";
	
	eOSType = utilsOsType.determine_os_type();
	if eOSType != utilsOsType.EnumOsType.Darwin:
		return (bOk, strMsg);
		
	strHeapDir = vstrFrameworkPythonDir + "/macosx/heap";
	strHeapDir = os.path.normcase( strHeapDir );
	if (os.path.exists( strHeapDir ) and os.path.isdir( strHeapDir )):
		return (bOk, strMsg);
		
	os.makedirs( strHeapDir );
	
	strRoot = vDictArgs[ "--srcRoot" ];
	strSrc = strRoot + "/examples/darwin/heap_find/heap/heap_find.cpp";
	shutil.copy( strSrc, strHeapDir );
	strSrc = strRoot + "/examples/darwin/heap_find/heap/Makefile";
	shutil.copy( strSrc, strHeapDir );
		
	return (bOk, strMsg);

#++---------------------------------------------------------------------------
# Details:	Create Python packages and Python __init__ files.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
#			vstrPkgDir				- (R) Destination for copied Python files.
#			vListPkgFiles			- (R) List of source Python files.
# Returns:	Bool - True = function success, False = failure.
#			Str - Error description on task failure.
# Throws:	None.
#--
def create_py_pkg( vDictArgs, vstrFrameworkPythonDir, vstrPkgDir, vListPkgFiles ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script create_py_pkg()" );
	dbg.dump_object( "Package file(s):", vListPkgFiles );
	bDbg = vDictArgs.has_key( "-d" );

	bOk = True;
	strMsg = "";
	
	if vstrPkgDir.__len__() != 0 and vstrPkgDir[ 0 ] != "/":
		bOk = False;
		strMsg = strErrMsgCreatePyPkgMissingSlash;
		return (bOk, strMsg);

	strPkgName = vstrPkgDir;
	strPkgName = "lldb" + strPkgName.replace( "/", "." );
	
	strPkgDir = vstrFrameworkPythonDir;
	strPkgDir += vstrPkgDir;
	strPkgDir = os.path.normcase( strPkgDir );
	
	if not(os.path.exists( strPkgDir ) and os.path.isdir( strPkgDir )):
		if bDbg:
			print(strMsgCreatePyPkgMkDir % strPkgDir);
		os.makedirs( strPkgDir );
		
	for strPkgFile in vListPkgFiles:
		if os.path.exists( strPkgFile ) and os.path.isfile( strPkgFile ):
			if bDbg:
				print(strMsgCreatePyPkgCopyPkgFile % (strPkgFile, strPkgDir));
			shutil.copy( strPkgFile, strPkgDir );
	
	# Create a packet init files if there wasn't one
	strPkgIniFile = strPkgDir + "/__init__.py";
	strPkgIniFile = os.path.normcase( strPkgIniFile );
	if os.path.exists( strPkgIniFile ) and os.path.isfile( strPkgIniFile ):
		return (bOk, strMsg);
	
	strPyScript = "__all__ = [";
	strDelimiter = "";
	for strPkgFile in vListPkgFiles:
		if os.path.exists( strPkgFile ) and os.path.isfile( strPkgFile ):
			strBaseName = os.path.basename( strPkgFile );
			nPos = strBaseName.find( "." );
			if nPos != -1:
				strBaseName = strBaseName[ 0 : nPos ];
			strPyScript += "%s\"%s\"" % (strDelimiter, strBaseName);
			strDelimiter = ",";
	strPyScript += "]\n";		
	strPyScript += "for x in __all__:\n";
	strPyScript += "\t__import__('%s.' + x)" % strPkgName;
	
	if bDbg:
		print(strMsgCreatePyPkgInitFile % strPkgIniFile);
	file = open( strPkgIniFile, "w" );
	file.write( strPyScript );
	file.close();
		
	return (bOk, strMsg);

#++---------------------------------------------------------------------------
# Details:	Copy the lldb.py file into the lldb package directory and rename 
#			to __init_.py.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
#			vstrCfgBldDir			- (R) Config directory path.
# Returns:	Bool - True = function success, False = failure.
#			Str - Error description on task failure.
# Throws:	None.
#--
def copy_lldbpy_file_to_lldb_pkg_dir( vDictArgs, vstrFrameworkPythonDir, vstrCfgBldDir ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script copy_lldbpy_file_to_lldb_pkg_dir()" );
	bOk = True;
	bDbg = vDictArgs.has_key( "-d" );
	strMsg = "";
	
	strSrc = vstrCfgBldDir + "/lldb.py";
	strSrc = os.path.normcase( strSrc );
	strDst = vstrFrameworkPythonDir + "/__init__.py";
	strDst = os.path.normcase( strDst );
	
	if not os.path.exists( strSrc ):
		strMsg = strErrMsgLLDBPyFileNotNotFound % strSrc;
		return (bOk, strMsg);
	
	try:
		if bDbg:
			print(strMsgCopyLLDBPy % (strSrc, strDst));
		shutil.copyfile( strSrc, strDst );
	except IOError as e:
		bOk = False;
		strMsg = "I/O error( %d ): %s %s" % (e.errno, e.strerror, strErrMsgCpLldbpy);
		if e.errno == 2:
			strMsg += " Src:'%s' Dst:'%s'" % (strSrc, strDst);
	except:
		bOk = False;
		strMsg = strErrMsgUnexpected % sys.exec_info()[ 0 ];
	
	return (bOk, strMsg);

#++---------------------------------------------------------------------------
# Details:	Make the symbolic that the script bridge for Python will need in 
# 			the Python framework directory. Code for specific to Windows.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
#			vstrDllName				- (R) File name for _lldb.dll.
# Returns:	Bool - True = function success, False = failure.
#			Str - Error description on task failure.
# Throws:	None.
#--
def make_symlink_windows( vDictArgs, vstrFrameworkPythonDir, vstrDllName ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script make_symlink_windows()" );
	bOk = True;
	strMsg = "";

	bDbg = vDictArgs.has_key( "-d" );
	strTarget = vstrDllName;
	# When importing an extension module using a debug version of python, you
	# write, for example, "import foo", but the interpreter searches for
	# "foo_d.pyd"
	if vDictArgs["--buildConfig"].lower() == "debug":
		strTarget += "_d";
	strTarget += ".pyd";
	strDLLPath = "%s\\%s" % (vstrFrameworkPythonDir, strTarget);
	strTarget = os.path.normcase( strDLLPath );
	strSrc = "";

	os.chdir( vstrFrameworkPythonDir );
	bMakeFileCalled = vDictArgs.has_key( "-m" );
	if not bMakeFileCalled:
		strSrc = os.path.normcase( "../../../LLDB" );
	else:
		strLibFileExtn = ".dll";
		strSrc = os.path.normcase( "../../../bin/liblldb%s" % strLibFileExtn );

	if os.path.isfile( strTarget ):
		if bDbg:
			print strMsglldbsoExists % strTarget;
		return (bOk, strMsg);

	if bDbg:
		print strMsglldbsoMk % (os.path.abspath(strSrc), os.path.abspath(strTarget));
		
	try:
		csl = ctypes.windll.kernel32.CreateHardLinkW
		csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
		csl.restype = ctypes.c_ubyte
		if csl(strTarget, strSrc, 0) == 0:
			raise ctypes.WinError()
	except Exception as e:
		bOk = False;
		strMsg = "WinError( %d ): %s %s" % (e.errno, e.strerror, strErrMsgMakeSymlink);
		strMsg += " Src:'%s' Target:'%s'" % (strSrc, strTarget);

	return (bOk, strMsg);
	
#++---------------------------------------------------------------------------
# Details:	Make the symbolic link that the script bridge for Python will need in 
# 			the Python framework directory. Code for all platforms apart from
#			Windows.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
#			vstrSoName				- (R) File name for _lldb.so.
# Returns:	Bool - True = function success, False = failure.
#			Str - Error description on task failure.
# Throws:	None.
#--
def make_symlink_other_platforms( vDictArgs, vstrFrameworkPythonDir, vstrSoPath ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script make_symlink_other_platforms()" );
	bOk = True;
	strMsg = "";
	bDbg = vDictArgs.has_key( "-d" );
	strTarget = vstrSoPath + ".so";
	strSoPath = "%s/%s" % (vstrFrameworkPythonDir, strTarget);
	strTarget = os.path.normcase( strSoPath );
	strSrc = "";
			
	os.chdir( vstrFrameworkPythonDir );
	bMakeFileCalled = vDictArgs.has_key( "-m" );
	if not bMakeFileCalled:
		strSrc = os.path.normcase( "../../../LLDB" );
	else:
		strLibFileExtn = "";
		eOSType = utilsOsType.determine_os_type();
		if eOSType == utilsOsType.EnumOsType.Linux:
			strLibFileExtn = ".so";
		elif eOSType == utilsOsType.EnumOsType.Darwin:
			strLibFileExtn = ".dylib";
		strSrc = os.path.normcase( "../../../liblldb%s" % strLibFileExtn );

	if os.path.islink( strTarget ):
		if bDbg:
			print strMsglldbsoExists % strTarget;
		return (bOk, strMsg);
	
	if bDbg:
		print strMsglldbsoMk;
		
	try:
		os.symlink( strSrc, strTarget );
	except OSError as e:
		bOk = False;
		strMsg = "OSError( %d ): %s %s" % (e.errno, e.strerror, strErrMsgMakeSymlink);
		strMsg += " Src:'%s' Target:'%s'" % (strSrc, strTarget);
	except:
		bOk = False;
		strMsg = strErrMsgUnexpected % sys.exec_info()[ 0 ];
	
	return (bOk, strMsg);
	
#++---------------------------------------------------------------------------
# Details:	Make the symlink that the script bridge for Python will need in 
# 			the Python framework directory.
# Args:		vDictArgs				- (R) Program input parameters.
# 			vstrFrameworkPythonDir	- (R) Python framework directory.
# Returns:	Bool - True = function success, False = failure.
#			strErrMsg - Error description on task failure.
# Throws:	None.
#--
def make_symlink( vDictArgs, vstrFrameworkPythonDir ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script make_symlink()" );
	bOk = True;
	strWkDir = "";
	strErrMsg = "";
	strSoFileName = "_lldb";
	 
	eOSType = utilsOsType.determine_os_type();
	if eOSType == utilsOsType.EnumOsType.Unknown:
		bOk = False;
		strErrMsg = strErrMsgOsTypeUnknown;
	elif eOSType == utilsOsType.EnumOsType.Windows:
		bOk, strErrMsg = make_symlink_windows( vDictArgs, 
											   vstrFrameworkPythonDir,
											   strSoFileName );
	else:
		bOk, strErrMsg = make_symlink_other_platforms( vDictArgs, 
													   vstrFrameworkPythonDir,
													   strSoFileName );		
	return (bOk, strErrMsg);

#++---------------------------------------------------------------------------
# Details:	Look for the directory in which to put the Python files; if it 
#			does not already exist, attempt to make it.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
# Returns:	Bool - True = function success, False = failure.
#			Str - Error description on task failure.
# Throws:	None.
#--
def find_or_create_python_dir( vDictArgs, vstrFrameworkPythonDir ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script find_or_create_python_dir()" );
	bOk = True;
	strMsg = "";
	bDbg = vDictArgs.has_key( "-d" );
	
	if os.path.isdir( vstrFrameworkPythonDir ):
		if bDbg:
			print strMsgFrameWkPyExists % vstrFrameworkPythonDir;
		return (bOk, strMsg);
		
	if bDbg:
		print strMsgFrameWkPyMkDir % vstrFrameworkPythonDir;
		
	try:
		os.makedirs( vstrFrameworkPythonDir );
	except OSError as exception:
		bOk = False;
		strMsg = strErrMsgCreateFrmWkPyDirFailed % (vstrFrameworkPythonDir,
													os.strerror( exception.errno ));
	
	return (bOk, strMsg);
	
#++---------------------------------------------------------------------------
# Details:	Retrieve the configuration build path if present and valid (using
#			parameter --cfgBlddir or copy the Python Framework directory.
# Args:		vDictArgs				- (R) Program input parameters.
#			vstrFrameworkPythonDir	- (R) Python framework directory.
# Returns:	Bool - True = function success, False = failure.
#			Str	- Config directory path.
#			strErrMsg - Error description on task failure.
# Throws:	None.
#--
def get_config_build_dir( vDictArgs, vstrFrameworkPythonDir ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script get_config_build_dir()" );
	bOk = True;
	strErrMsg = "";
	
	strConfigBldDir = "";
	bHaveConfigBldDir = vDictArgs.has_key( "--cfgBldDir" );
	if bHaveConfigBldDir:
		strConfigBldDir = vDictArgs[ "--cfgBldDir" ];
	if (bHaveConfigBldDir == False) or (strConfigBldDir.__len__() == 0):
		strConfigBldDir = vstrFrameworkPythonDir;
	
	return (bOk, strConfigBldDir, strErrMsg);

#++---------------------------------------------------------------------------
# Details:	Determine where to put the files. Retrieve the directory path for 
#			Python's dist_packages/	site_package folder on a Windows platform.
# Args:		vDictArgs	- (R) Program input parameters.
# Returns:	Bool - True = function success, False = failure.
#			Str	- Python Framework directory path.
#			strErrMsg - Error description on task failure.
# Throws:	None.
#--
def get_framework_python_dir_windows( vDictArgs ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script get_framework_python_dir_windows()" );
	bOk = True;
	strWkDir = "";
	strErrMsg = "";
	 
	# We are being built by LLVM, so use the PYTHON_INSTALL_DIR argument,
	# and append the python version directory to the end of it.  Depending 
	# on the system other stuff may need to be put here as well.
	from distutils.sysconfig import get_python_lib;
	strPythonInstallDir = "";
	bHaveArgPrefix = vDictArgs.has_key( "--prefix" );
	if bHaveArgPrefix: 
		strPythonInstallDir = vDictArgs[ "--prefix" ];

	bHaveArgCmakeBuildConfiguration = vDictArgs.has_key( "--cmakeBuildConfiguration" );
	if bHaveArgCmakeBuildConfiguration:
		strPythonInstallDir += '/' + vDictArgs[ "--cmakeBuildConfiguration" ];

	if strPythonInstallDir.__len__() != 0:
		strWkDir = get_python_lib( True, False, strPythonInstallDir );
	else:
		strWkDir = get_python_lib( True, False );
	strWkDir += "/lldb";
	strWkDir = os.path.normcase( strWkDir );
	
	return (bOk, strWkDir, strErrMsg);

#++---------------------------------------------------------------------------
# Details:	Retrieve the directory path for Python's dist_packages/
#			site_package folder on a UNIX style platform.
# Args:		vDictArgs	- (R) Program input parameters.
# Returns:	Bool - True = function success, False = failure.
#			Str	- Python Framework directory path.
#			strErrMsg - Error description on task failure.
# Throws:	None.
#--
def get_framework_python_dir_other_platforms( vDictArgs ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script get_framework_python_dir_other_platform()" );
	bOk = True;
	strWkDir = "";
	strErrMsg = "";
	bDbg = vDictArgs.has_key( "-d" );
	
	bMakeFileCalled = vDictArgs.has_key( "-m" );
	if bMakeFileCalled:
		dbg.dump_text( "Built by LLVM" );
		return get_framework_python_dir_windows( vDictArgs );
	else:
		dbg.dump_text( "Built by XCode" );
		# We are being built by XCode, so all the lldb Python files can go
		# into the LLDB.framework/Resources/Python subdirectory.
		strWkDir = vDictArgs[ "--targetDir" ];
		strWkDir += "/LLDB.framework";
		if os.path.exists( strWkDir ):
			if bDbg:
				print strMsgFoundLldbFrameWkDir % strWkDir;
			strWkDir += "/Resources/Python/lldb";
			strWkDir = os.path.normcase( strWkDir );
		else:
			bOk = False;
			strErrMsg = strErrMsgFrameWkPyDirNotExist % strWkDir;	
	
	return (bOk, strWkDir, strErrMsg);

#++---------------------------------------------------------------------------
# Details:	Retrieve the directory path for Python's dist_packages/
#			site_package folder depending on the type of OS platform being 
#			used.
# Args:		vDictArgs	- (R) Program input parameters.
# Returns:	Bool - True = function success, False = failure.
#			Str	- Python Framework directory path.
#			strErrMsg - Error description on task failure.
# Throws:	None.
#--
def get_framework_python_dir( vDictArgs ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script get_framework_python_dir()" );
	bOk = True;
	strWkDir = "";
	strErrMsg = "";
	 
	eOSType = utilsOsType.determine_os_type();
	if eOSType == utilsOsType.EnumOsType.Unknown:
		bOk = False;
		strErrMsg = strErrMsgOsTypeUnknown;
	elif eOSType == utilsOsType.EnumOsType.Windows:
		bOk, strWkDir, strErrMsg = get_framework_python_dir_windows( vDictArgs );
	else:
		bOk, strWkDir, strErrMsg = get_framework_python_dir_other_platforms( vDictArgs );
			
	return (bOk, strWkDir, strErrMsg);

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------

""" Details: Program main entry point fn. Called by another Python script.
	
	--------------------------------------------------------------------------
	Details: This script is to be called by another Python script. It is not
			 intended to be called directly i.e from the command line.
	Args:	vDictArgs	- (R) Map of parameter names to values.
			-d (optional)	Determines whether or not this script 
							outputs additional information when running.
			-m (optional) 	Specify called from Makefile system. If given locate
							the LLDBWrapPython.cpp in --srcRoot/source folder 
							else in the	--targetDir folder.
			--buildConfig	The LLDB build configuration (e.g. debug/release).
			--srcRoot		The root of the lldb source tree.
			--targetDir 	Where the lldb framework/shared library gets put.
			--cfgBlddir 	Where the buildSwigPythonLLDB.py program will 
			(optional) 		put the lldb.py file it generated from running 
							SWIG.
			--prefix  		Is the root directory used to determine where 
			(optional)		third-party modules for scripting languages should 
							be installed. Where non-Darwin systems want to put 
							the .py and .so files so that Python can find them 
							automatically. Python install directory.
	Results:	0 		Success
				-100+	Error from this script to the caller script.
				-100	Error program failure with optional message.
				
	--------------------------------------------------------------------------
							
"""
def main( vDictArgs ):
	dbg = utilsDebug.CDebugFnVerbose( "Python script main()" );
	bOk = True;
	strMsg = "";
	strErrMsgProgFail = "";
	
	bDbg = vDictArgs.has_key( "-d" );
	
	eOSType = utilsOsType.determine_os_type();
	if bDbg:
		pyVersion = sys.version_info;
		print(strMsgOsVersion % utilsOsType.EnumOsType.name_of( eOSType ));
		print(strMsgPyVersion % (pyVersion[ 0 ], pyVersion[ 1 ]));
	
	bOk, strFrameworkPythonDir, strMsg = get_framework_python_dir( vDictArgs );

	if bOk:
		bOk, strCfgBldDir, strMsg = get_config_build_dir( vDictArgs, strFrameworkPythonDir );
	if bOk and bDbg:
		print strMsgPyFileLocatedHere % strFrameworkPythonDir;
		print strMsgConfigBuildDir % strCfgBldDir;
	
	if bOk:
		bOk, strMsg = find_or_create_python_dir( vDictArgs, strFrameworkPythonDir );
	
	if bOk:
		bOk, strMsg = make_symlink( vDictArgs, strFrameworkPythonDir );
	
	if bOk:
		bOk, strMsg = copy_lldbpy_file_to_lldb_pkg_dir( vDictArgs,
														strFrameworkPythonDir,
														strCfgBldDir );
	strRoot = vDictArgs[ "--srcRoot" ];
	if bOk:
		# lldb
		listPkgFiles = [ strRoot + "/source/Interpreter/embedded_interpreter.py" ];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "", listPkgFiles );
	
	if bOk:
		# lldb/formatters/cpp
		listPkgFiles = [ strRoot + "/examples/synthetic/gnu_libstdcpp.py",
						 strRoot + "/examples/synthetic/libcxx.py" ];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "/formatters/cpp", listPkgFiles );
	
	if bOk:
		# Make an empty __init__.py in lldb/runtime as this is required for 
		# Python to recognize lldb.runtime as a valid package (and hence,
		# lldb.runtime.objc as a valid contained package)
		listPkgFiles = [];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "/runtime", listPkgFiles );
	
	if bOk:
		# lldb/formatters
		# Having these files copied here ensure that lldb/formatters is a 
		# valid package itself
		listPkgFiles = [ strRoot + "/examples/summaries/cocoa/cache.py", 
						 strRoot + "/examples/summaries/cocoa/metrics.py",
						 strRoot + "/examples/summaries/cocoa/attrib_fromdict.py",
						 strRoot + "/examples/summaries/cocoa/Logger.py" ];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "/formatters", listPkgFiles );
	
	if bOk:
		# lldb/utils
		listPkgFiles = [ strRoot + "/examples/python/symbolication.py" ];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "/utils", listPkgFiles );
	
	if bOk and (eOSType == utilsOsType.EnumOsType.Darwin):
		# lldb/macosx
		listPkgFiles = [ strRoot + "/examples/python/crashlog.py",
						 strRoot + "/examples/darwin/heap_find/heap.py" ];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "/macosx", listPkgFiles );
	
	if bOk and (eOSType == utilsOsType.EnumOsType.Darwin):
		# lldb/diagnose
		listPkgFiles = [ strRoot + "/examples/python/diagnose_unwind.py",
						 strRoot + "/examples/python/diagnose_nsstring.py" ];
		bOk, strMsg = create_py_pkg( vDictArgs, strFrameworkPythonDir, "/diagnose", listPkgFiles );
	
	if bOk:
		bOk, strMsg = macosx_copy_file_for_heap( vDictArgs, strFrameworkPythonDir );
	
	if bOk:
		return (0, strMsg );
	else:
		strErrMsgProgFail += strMsg;
		return (-100, strErrMsgProgFail );

	
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------

# This script can be called by another Python script by calling the main() 
# function directly
if __name__ == "__main__":
	print "Script cannot be called directly, called by finishSwigWrapperClasses.py";
	
