'''Main Nimp modules'''

from pathlib import Path

# you can use os.path and open() as well
__version__ = Path(__file__).parent.joinpath("VERSION").read_text(encoding='utf-8')

__all__ = [
    'nimp_cli',
    'base_commands',
    'base_platforms',
    'sys',
    'unreal_engine',
    'utils',
    'tests',
]
