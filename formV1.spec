# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import pypylon
import pathlib

pypylon_dir = pathlib.Path(pypylon.__file__).parent
pypylon_dlls = [(str(dll), '.') for dll in pypylon_dir.glob('*.dll')]
pypylon_pyds = [(str(dll), '.') for dll in pypylon_dir.glob('*.pyd')]

a = Analysis(['formV1.py'],
             pathex=['C:\\Users\\devin.jiang\\Devin\\Programme\\PC\\Python\\Marian-master\\marian v1.2'],
             binaries=pypylon_dlls,
             datas=[],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='formV1',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
