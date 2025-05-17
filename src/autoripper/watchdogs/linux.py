"""
Utilities for ripping titles

"""

import logging

import pyudev

from automakemkv import UUID_ROOT

from . import RUNNING
from .base import BaseWatchdog

KEY = 'DEVNAME'
CHANGE = 'DISK_MEDIA_CHANGE'
STATUS = "ID_CDROM_MEDIA_STATE"
EJECT = "DISK_EJECT_REQUEST"  # This appears when initial eject requested
READY = "SYSTEMD_READY"  # This appears when disc tray is out


class Watchdog(BaseWatchdog):
    """
    Main watchdog for disc monitoring/ripping

    """

    def __init__(
        self,
        progress_dialog,
        audio: dict | None = None,
        video: dict | None = None,
        root: str = UUID_ROOT,
        **kwargs,
    ):
        """
        Arguments:
            outdir (str) : Top-level directory for ripping files

        Keyword arguments:
            video (dict): Option for video. These include:
                everything (bool) : If set, then all titles identified
                    for ripping will be ripped. By default, only the
                    main feature will be ripped
                extras (bool) : If set, only 'extra' features will
                    be ripped along with the main title(s). Main
                    title(s) include Theatrical/Extended/etc.
                    versions for movies, and episodes for series.
                root (str) : Location of the 'by-uuid' directory
                    where discs are mounted. This is used to
                    get the unique ID of the disc.
                convention (str) : File naming convention for video files
            audio (dict): options for audio

        """

        super().__init__()
        self.log = logging.getLogger(__name__)
        self.log.debug("%s started", __name__)

        self.HANDLE_DISC.connect(self.handle_disc)

        self.video = video or {}
        self.audio = audio or {}

        self.root = root
        self.progress_dialog = progress_dialog

        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem='block')

    def run(self):
        """
        Processing for thread

        Polls udev for device changes, running MakeMKV pipelines
        when dvd/bluray found

        """

        self.log.info('Watchdog thread started')
        while not RUNNING.is_set():
            device = self._monitor.poll(timeout=1.0)
            if device is None:
                continue

            # Get value for KEY. If is None, then did not exist, so continue
            dev = device.properties.get(KEY, None)
            if dev is None:
                continue

            if device.properties.get(EJECT, ''):
                self.log.debug("%s - Eject request", dev)
                self._ejecting(dev)
                continue

            if device.properties.get(READY, '') == '0':
                self.log.debug("%s - Drive is ejected", dev)
                self._ejecting(dev)
                continue

            if device.properties.get(CHANGE, '') != '1':
                self.log.debug(
                    "%s - Not a '%s' event, ignoring",
                    dev,
                    CHANGE,
                )
                continue

            status = device.properties.get(STATUS, '')
            if status not in ('', 'complete'):
                self.log.debug(
                    "%s - Caught event that was NOT insert/eject, ignoring",
                    dev,
                )
                continue

            if dev in self._mounted:
                self.log.info("%s - Device in mounted list", dev)
                continue

            self.log.debug("%s - Finished mounting", dev)
            self._mounted[dev] = None
            self.HANDLE_DISC.emit(
                dev,
                'video' if status == 'complete' else 'audio',
            )
