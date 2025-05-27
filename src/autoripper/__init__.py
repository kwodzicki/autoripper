import logging
from logging.handlers import RotatingFileHandler

import os
import sys
from importlib.metadata import metadata as pkg_metadata

try:
    import cdripper
except Exception:
    cdripper = None

try:
    import automakemkv
except Exception:
    automakemkv = None

NAME = 'autoripper'

if cdripper:
    cdripper.NAME = NAME

if automakemkv:
    automakemkv.NAME = NAME

HOMEDIR = os.path.expanduser('~')

RESOURCES = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    'resources',
)

HOMEDIR = os.path.expanduser('~')
OUTDIR = os.path.join(HOMEDIR, 'Videos')
DBDIR = os.path.join(
    HOMEDIR,
    f".{__name__}DB",
)

TRAY_ICON = os.path.join(RESOURCES, "tray_icon.png")
if sys.platform.startswith('linux'):
    APPDIR = os.path.join(
        HOMEDIR,
        'Library',
        'Application Support',
        __name__,
    )
    APP_ICON = os.path.join(RESOURCES, "app_icon_linux.png")
elif sys.platform.startswith('win'):
    APPDIR = os.path.join(
        HOMEDIR,
        'AppData',
        'Local',
        __name__,
    )
    APP_ICON = os.path.join(RESOURCES, "app_icon_windows.png")
else:
    raise Exception(
        f"System platform '{sys.platform}' not currently supported"
    )

LOGDIR = os.path.join(
    APPDIR,
    'logs',
)

os.makedirs(APPDIR, exist_ok=True)
os.makedirs(LOGDIR, exist_ok=True)

TEST_DATA_FILE = os.path.join(
    APPDIR,
    'testing.txt',
)
SETTINGS_FILE = os.path.join(
    APPDIR,
    'settings.json',
)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

STREAM = logging.StreamHandler()
STREAM.setLevel(logging.WARNING)
STREAM.setFormatter(
    logging.Formatter(
        '%(asctime)s [%(levelname).4s] %(message)s'
    )
)

ROTFILE = RotatingFileHandler(
    os.path.join(LOGDIR, f"{__name__}.log"),
    maxBytes=500*2**10,
    backupCount=5,
)
ROTFILE.setLevel(logging.INFO)
ROTFILE.setFormatter(
    logging.Formatter(
        '%(asctime)s [%(levelname).4s] {%(name)s.%(funcName)s} %(message)s'
    )
)

LOG.addHandler(STREAM)
LOG.addHandler(ROTFILE)

if cdripper:
    cdripper.LOG.removeHandler(cdripper.STREAM)
    cdripper.LOG.removeHandler(cdripper.ROTFILE)
    cdripper.LOG.addHandler(STREAM)
    cdripper.LOG.addHandler(ROTFILE)

if automakemkv:
    automakemkv.LOG.removeHandler(automakemkv.STREAM)
    automakemkv.LOG.removeHandler(automakemkv.ROTFILE)
    automakemkv.LOG.addHandler(STREAM)
    automakemkv.LOG.addHandler(ROTFILE)

meta = pkg_metadata(__name__)
__version__ = meta.json['version']
__url__ = meta.json['project_url'][0].split(',')[1].strip()

del meta
