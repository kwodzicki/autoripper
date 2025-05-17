"""
Utilities for ripping titles

"""

import logging
import signal
from threading import Event

from PyQt5 import QtCore

import pyudev

from automakemkv import OUTDIR as VIDEO_OUTDIR, UUID_ROOT, DBDIR
from automakemkv.ripper import DiscHandler as VideoDiscHandler
from automakemkv.ui import dialogs as video_dialogs

from cdripper import OUTDIR as AUDIO_OUTDIR
from cdripper.ripper import DiscHandler as AudioDiscHandler

KEY = 'DEVNAME'
CHANGE = 'DISK_MEDIA_CHANGE'
STATUS = "ID_CDROM_MEDIA_STATE"
EJECT = "DISK_EJECT_REQUEST"  # This appears when initial eject requested
READY = "SYSTEMD_READY"  # This appears when disc tray is out

RUNNING = Event()

signal.signal(signal.SIGINT, lambda *args: RUNNING.set())
signal.signal(signal.SIGTERM, lambda *args: RUNNING.set())


class UdevWatchdog(QtCore.QThread):
    """
    Main watchdog for disc monitoring/ripping

    """

    # Dev device and disc type string
    HANDLE_DISC = QtCore.pyqtSignal(str, str)

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

        self._mounting = {}
        self._mounted = {}
        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem='block')

    @property
    def video_outdir(self):
        return self.video.get('outdir', None)

    @video_outdir.setter
    def video_outdir(self, val):
        self.log.info('Video output directory set to : %s', val)
        self.video['outdir'] = val

    @property
    def audio_outdir(self):
        return self.audio.get('outdir', None)

    @audio_outdir.setter
    def audio_outdir(self, val):
        self.log.info('Audio output directory set to : %s', val)
        self.audio['outdir'] = val

    def set_settings(self, **kwargs):
        """
        Set options for ripping discs

        """

        self.log.debug('Updating ripping options')
        self.video.update(
            kwargs.get('video', {})
        )
        self.audio.update(
            kwargs.get('audio', {})
        )

    def get_settings(self):

        return {
            'video': self.video,
            'audio': self.audio,
        }

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

    def _ejecting(self, dev):

        proc = self._mounted.pop(dev, None)
        if proc is None:
            return

        if proc.isRunning():
            self.log.warning("%s - Killing the ripper process!", dev)
            proc.terminate(dev)
            return

    def quit(self, *args, **kwargs):
        RUNNING.set()

    def video_rip_failure(self, device: str):

        dialog = video_dialogs.RipFailure(device)
        dialog.exec_()

    def video_rip_success(self, device: str):

        dialog = video_dialogs.RipSuccess(device)
        dialog.exec_()

    @QtCore.pyqtSlot(str, str)
    def handle_disc(self, dev: str, disc_type: str):
        """
        Arguments:
            dev (str): Dev device
            disc_type (str): Type of disc, either audio or video

        """

        if disc_type == 'video':
            self.log.info("%s - Assuming video disc inserted", dev)
            obj = VideoDiscHandler(
                dev,
                self.video.get('outdir', VIDEO_OUTDIR),
                self.video.get('everything', False),
                self.video.get('extras', False),
                self.video.get('dbdir', DBDIR),
                self.root,
                self.video.get('convention', 'video_utils'),
                self.progress_dialog,
            )
            obj.FAILURE.connect(self.video_rip_failure)
            obj.SUCCESS.connect(self.video_rip_success)
            self._mounted[dev] = obj

        elif disc_type == 'audio':
            self.log.info("%s - Assuming audio disc inserted", dev)
            self._mounted[dev] = AudioDiscHandler(
                dev,
                self.audio.get('outdir', AUDIO_OUTDIR),
                self.progress_dialog,
            )
        else:
            self.log.warning("%s - Unrecognized disc_type: %s", dev, disc_type)
