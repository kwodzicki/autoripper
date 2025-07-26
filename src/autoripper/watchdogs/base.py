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
    from cdripper.ripper import DiscHandler as AudioDiscHandler
except Exception:
    AudioDiscHandler = None

try:
    from automakemkv import UUID_ROOT
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
        root: str | None = UUID_ROOT,
        **kwargs,
    ):
        """
        Arguments:
            outdir (str) : Top-level directory for ripping files

        Keyword arguments:

        """

        super().__init__()
        self.log = logging.getLogger(__name__)
        self.log.debug("%s started", __name__)

        self.HANDLE_INSERT.connect(self.handle_insert)

        self.progress = progress
        self.root = root

        self._mounted = []
        self._failure = []
        self._success = []

    def quit(self, *args, **kwargs):
        RUNNING.set()

    @QtCore.pyqtSlot(str)
    def video_rip_failure(self, fname: str):

        sender = self.sender()
        sender.wait()  # Wait for thread to finish
        dev = sender.dev
        dialog = video_dialogs.RipFailure(dev, fname)
        self._failure.append(dialog)
        dialog.FINISHED.connect(self._failure_closed)
        dialog.exec_()

    @QtCore.pyqtSlot(int)
    def _failure_closed(self, res: int):
        obj = self.sender()
        if obj in self._failure:
            self._failure.remove(obj)
        obj.deleteLater()

    @QtCore.pyqtSlot(str)
    def video_rip_success(self, fname: str):

        sender = self.sender()
        sender.wait()  # Wait for thread to finish
        dev = sender.dev
        dialog = video_dialogs.RipSuccess(dev, fname)
        self._success.append(dialog)
        dialog.FINISHED.connect(self._success_closed)
        dialog.exec_()

    @QtCore.pyqtSlot(int)
    def _success_closed(self, res: int):
        obj = self.sender()
        if obj in self._success:
            self._success.remove(obj)
        obj.deleteLater()

    @QtCore.pyqtSlot()
    def rip_finished(self):

        sender = self.sender()
        sender.wait()  # Wait for thread to finish
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
                    dev,
                )
                return

            self.log.info("%s - Assuming video disc inserted", dev)
            obj = VideoDiscHandler(
                dev,
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
