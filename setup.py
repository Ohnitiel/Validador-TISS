import sys
from os.path import expanduser
from cx_Freeze import setup, Executable

target_name = 'Validador TISS'

with open("../compile_path.txt") as f:
    path = f'{f.readline()}\\{target_name}'

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [
    Executable('main.pyw', base=base, target_name=target_name,
               icon='TISS.ico')
]

setup(
    name=target_name,
    version='1.0',
    description='Validador TISS',
    executables=executables,
    options={"build_exe": {
        "packages": ["multiprocessing"],
        # "build_exe": path,
        "includes": "atexit",
        "zip_include_packages": ["*"],
        "zip_exclude_packages": [],
    }},
)
