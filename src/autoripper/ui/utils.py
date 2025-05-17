import logging
import os
import re
import json

from automakemkv import DBDIR, OUTDIR as VIDEO_OUTDIR
from cdripper import OUTDIR as AUDIO_OUTDIR

from .. import SETTINGS_FILE

EXT = '.json'
TRACKSIZE_AP = 11  # Number used for track size in TINFO from MakeMKV
TRACKSIZE_REG = re.compile(
    rf"TINFO:(\d+),{TRACKSIZE_AP},\d+,\"(\d+)\"",
)


def load_settings() -> dict:
    """
    Load dict from data JSON file

    Returns:
        dict: Settings data loaded from JSON file

    """

    if not os.path.isfile(SETTINGS_FILE):
        video_settings = {
            'dbdir': DBDIR,
            'outdir': VIDEO_OUTDIR,
            'everything': False,
            'extras': False,
            'show_status': True,
            'convention': 'video_utils',
        }
        audio_settings = {
            'outdir': AUDIO_OUTDIR,
        }

        settings = {
            'video': video_settings,
            'audio': audio_settings,
        }
        save_settings(settings)
        return settings

    logging.getLogger(__name__).debug(
        'Loading settings from %s', SETTINGS_FILE,
    )
    with open(SETTINGS_FILE, 'r') as fid:
        return json.load(fid)


def save_settings(settings: dict) -> None:
    """
    Save dict to JSON file

    Arguments:
        settings (dict): Settings to save to JSON file

    """

    logging.getLogger(__name__).debug(
        'Saving settings to %s', SETTINGS_FILE,
    )
    with open(SETTINGS_FILE, 'w') as fid:
        json.dump(settings, fid)


def get_vendor_model(path: str) -> tuple[str]:
    """
    Get the vendor and model of drive

    """

    path = os.path.join(
        '/sys/class/block/',
        os.path.basename(path),
        'device',
    )

    vendor = os.path.join(path, 'vendor')
    if os.path.isfile(vendor):
        with open(vendor, mode='r') as iid:
            vendor = iid.read()
    else:
        vendor = ''

    model = os.path.join(path, 'model')
    if os.path.isfile(model):
        with open(model, mode='r') as iid:
            model = iid.read()
    else:
        model = ''

    return vendor.strip(), model.strip()
