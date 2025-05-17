"""
Utilities for ripping titles

"""

import logging

from PyQt5 import QtCore

from automakemkv import OUTDIR as VIDEO_OUTDIR, DBDIR
from automakemkv.ripper import DiscHandler as VideoDiscHandler
from automakemkv.ui import dialogs as video_dialogs

from cdripper import OUTDIR as AUDIO_OUTDIR
from cdripper.ripper import DiscHandler as AudioDiscHandler

from . import RUNNING


class BaseWatchdog(QtCore.QThread):
    """
    Main watchdog for disc monitoring/ripping

    """

    # Dev device and disc type string
    HANDLE_DISC = QtCore.pyqtSignal(str, str)

    def __init__(self):
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

        self.video = {}
        self.audio = {}

        self.root = None
        self.progress_dialog = None

        self._mounting = {}
        self._mounted = {}

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
                self.video.get('convention', 'video_utils'),
                self.video.get('dbdir', DBDIR),
                self.root,
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
