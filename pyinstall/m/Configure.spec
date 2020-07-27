# -*- mode: python ; coding: utf-8 -*-

"""
MIT License

Copyright (c) 2020 PyKOB - MorseKOB in Python

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from os import environ
from pathlib import Path

block_cipher = None

project_folder = Path('../..').resolve()
pykob_folder = project_folder / 'pykob'
pykob_data_folder = pykob_folder / 'data'
pykob_data = pykob_data_folder / '*'
pykob_resources_folder = pykob_folder / 'resources'
pykob_resources = pykob_resources_folder / '*'
configure_app = project_folder / 'Configure.py'

print('Project:', project_folder)
print('Configure App:', configure_app)
print('PyKOB:', pykob_folder)
print('PyKOB Data:', pykob_data)
print('PyKOB Resources:', pykob_resources)

data_files = [
    (pykob_data, 'pykob/data'), 
    (pykob_resources, 'pykob/resources')
]
print('Data Files:', data_files)

a = Analysis([str(configure_app)],
             pathex=[project_folder],
             binaries=[],
             datas=data_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Configure',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Configure')
