# -*- coding: UTF-8 -*-
__author__ = 'FinalTheory'

from distutils.core import setup
from glob import glob
import py2exe
import certifi
import sys
import os

sys.path.append(r'C:\VS2013\VC\redist\x64\Microsoft.VC120.CRT')


def copy_dir(base_dir):
    for (dirpath, dirnames, files) in os.walk(base_dir):
        yield (dirpath, [os.path.join(dirpath, f) for f in files])


data_files = [
    ("Microsoft.VC120.CRT", glob(r'C:\VS2013\VC\redist\x64\Microsoft.VC120.CRT\*.*')),
    ("", ['config.ini', 'InitDataBase.sql', 'wget.exe', 'aria2c.exe']),
    ("", [certifi.where()])
]

data_files.extend([item for item in copy_dir('static')])

options = {"py2exe": {
    "compressed": 1,
    "optimize": 2,
    # 在Win7上需要设置为3，即不打包，否则会导致无法导入模块
    "bundle_files": 1,
}}

setup(
    version="1.0.0",
    name="PicDownloader",
    description="Download server based on web.py and aria2",
    options=options,
    data_files=data_files,
    console=[
        {
            "script": "Main.py",
            "icon_resources": [(1, "icon.ico")]
        },
        {
            "script": os.path.join("test", "test_webfunc.py"),
            "icon_resources": [(1, "test.ico")]
        },
    ],
)

# Add the "zoneinfo" directory to the library.zip

import pytz
import zipfile

zipfile_path = os.path.join("dist", 'library.zip')
z = zipfile.ZipFile(zipfile_path, 'a')
zoneinfo_dir = os.path.join(os.path.dirname(pytz.__file__), 'zoneinfo')
disk_basedir = os.path.dirname(os.path.dirname(pytz.__file__))
for absdir, directories, filenames in os.walk(zoneinfo_dir):
    assert absdir.startswith(disk_basedir), (absdir, disk_basedir)
    zip_dir = absdir[len(disk_basedir):]
    for f in filenames:
        z.write(os.path.join(absdir, f), os.path.join(zip_dir, f))

z.close()
