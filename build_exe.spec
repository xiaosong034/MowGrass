# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['game_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('思源黑体', '思源黑体'),  # 包含字体文件夹
    ],
    hiddenimports=[
        'pygame',
        'i18n',
        'characters',
        'boss',
        'meta_systems',
        'dialogue_system',
        'gacha_animation',
        'town_map',
        'grass_cutting_game',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='割草游戏',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
)
