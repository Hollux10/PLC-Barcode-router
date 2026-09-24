[app]

# (str) Title of your application
title = PLC Barcode Router

# (str) Package name
package.name = plcrouter

# (str) Package domain (needed for android/ios packaging)
package.domain = com.company.plcrouter

# (str) Source code where the main.py live
source.dir = .

# (str) Application version
version = 0.1


# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,html,js,css,db,txt,spec,json

# (list) List of directory to include
source.include_dirs = templates, static

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,fastapi,uvicorn,jinja2,pydantic,python-multipart,sqlite3

# (str) Custom source folders for requirements
# Sets custom source for any requirement with recipes or site-packages

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE, FOREGROUND_SERVICE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API required
android.minapi = 21

# (str) Android NDK architecture to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Enable AndroidX support. Required when targeting Android 28+
android.enable_androidx = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = error, 1 = warning)
warn_on_root = 1
