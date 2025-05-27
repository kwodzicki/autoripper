"""
Utilities for ripping titles

"""

import logging
import sys
from subprocess import Popen

from PyQt5 import QtCore

if sys.platform.startswith('win'):
    import ctypes

try:
    from cdripper import OUTDIR as AUDIO_OUTDIR
    from cdripper.ripper import DiscHandler as AudioDiscHandler
except Exception:
    AudioDiscHandler = None

try:
    from automakemkv import OUTDIR as VIDEO_OUTDIR, DBDIR, UUID_ROOT
    from automakemkv.ripper import DiscHandler as VideoDiscHandler
    from automakemkv.ui import dialogs as video_dialogs
except Exception:
    UUID_ROOT = None
    VideoDiscHandler = None

from . import RUNNING


class BaseWatchdog(QtCore.QThread):
    """
    Main watchdog for disc monitoring/ripping

    """

    # Dev device and disc type string
    HANDLE_INSERT = QtCore.pyqtSignal(str, str)

    def __init__(
        self,
        progress,
        *args,
        video: dict | None = None,
        audio: dict | None = None,
        root: str | None = UUID_ROOT,
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

        self.HANDLE_INSERT.connect(self.handle_insert)

        self.video = video or {}
        self.audio = audio or {}

        self.progress = progress
        self.root = root

        self._mounted = []

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

    def quit(self, *args, **kwargs):
        RUNNING.set()

    @QtCore.pyqtSlot()
    def video_rip_failure(self):

        dev = self.sender().dev
        dialog = video_dialogs.RipFailure(dev)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def video_rip_success(self):

        dev = self.sender().dev
        dialog = video_dialogs.RipSuccess(dev)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def rip_finished(self):

        sender = self.sender()
        self.log.debug("%s - Processing finished event", sender.dev)
        sender.cancel(sender.dev)
        if sender in self._mounted:
            self._mounted.remove(sender)
        else:
            self.log.warning(
                "%s - Did not find sender object in _mounted",
                sender.dev,
            )

        sender.deleteLater()

    @QtCore.pyqtSlot(str, str)
    def handle_insert(self, dev: str, disc_type: str):
        """
        Arguments:
            dev (str): Dev device
            disc_type (str): Type of disc, either audio or video

        """

        if disc_type == 'video':
            if VideoDiscHandler is None:
                self.log.error(
                    "%s - The 'autoMakeMKV' program was not imported. "
                    "Are you sure it is installed? Unable to process "
                    "video discs (DVD/Blu-ray)!",
                    self.dev,
                )
                return

            self.log.info("%s - Assuming video disc inserted", dev)
            obj = VideoDiscHandler(
                dev,
                self.video.get('outdir', VIDEO_OUTDIR),
                self.video.get('everything', False),
                self.video.get('extras', False),
                self.video.get('convention', 'video_utils'),
                self.video.get('dbdir', DBDIR),
                self.root,
                self.progress,
            )
            obj.FAILURE.connect(self.video_rip_failure)
            obj.SUCCESS.connect(self.video_rip_success)
            obj.FINISHED.connect(self.rip_finished)
            obj.EJECT_DISC.connect(self.eject_disc)
            self._mounted.append(obj)

        elif disc_type == 'audio':
            if AudioDiscHandler is None:
                self.log.error(
                    "%s - The 'cdRipper' program was not imported. "
                    "Are you sure it is installed? Unable to process "
                    "audio discs (CD)!",
                    self.dev,
                )
                return

            self.log.info("%s - Assuming audio disc inserted", dev)
            obj = AudioDiscHandler(
                dev,
                self.progress,
                outdir=self.audio.get('outdir', AUDIO_OUTDIR),
            )
            obj.FINISHED.connect(self.rip_finished)
            obj.EJECT_DISC.connect(self.eject_disc)
            self._mounted.append(obj)

        else:
            self.log.warning("%s - Unrecognized disc_type: %s", dev, disc_type)

    @QtCore.pyqtSlot()
    def eject_disc(self) -> None:
        """
        Eject the disc

        """

        dev = self.sender().dev
        self.log.debug("%s - Ejecting disc", dev)

        if sys.platform.startswith('linux'):
            _ = Popen(['eject', dev])
        elif sys.platform.startswith('win'):
            command = f"open {dev}: type CDAudio alias drive"
            ctypes.windll.winmm.mciSendStringW(command, None, 0, None)
            ctypes.windll.winmm.mciSendStringW(
                "set drive door open",
                None,
                0,
                None,
            )
            ctypes.windll.winmm.mciSendStringW("close drive", None, 0, None)
