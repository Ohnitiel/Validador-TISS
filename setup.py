import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [
    Executable('main.pyw', base=base, targetName='Validador TISS',
               icon="TISS.ico")
]

setup(
    name='Validador TISS',
    version='1.1',
    description='Validador TISS personalizado Qualifisio',
    executables=executables,
    options={"build_exe": {
        "packages": ["multiprocessing"],
        "include_files": [('xsd', 'xsd')],
        "build_exe": r"C:\Users\Qualifisio\Desktop\Validador TISS 2",
        "includes": "atexit",
    }},
)
