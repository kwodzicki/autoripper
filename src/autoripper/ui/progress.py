import logging
from subprocess import Popen

from PyQt5 import QtWidgets
from PyQt5 import QtCore

from automakemkv.ui.progress import ProgressWidget as VideoProgressWidget
from cdripper.ui.progress import ProgressWidget as AudioProgressWidget


class ProgressDialog(QtWidgets.QWidget):

    # First arg in dev, second is all info
    MKV_ADD_DISC = QtCore.pyqtSignal(str, dict, bool)
    # Arg is dev of disc to remove
    MKV_REMOVE_DISC = QtCore.pyqtSignal(str)
    # Args are dev of disc to attach process to and the process
    MKV_NEW_PROCESS = QtCore.pyqtSignal(str, Popen, str)
    # First arg is dev, second is track num
    MKV_CUR_TRACK = QtCore.pyqtSignal(str, str)
    # First arg is dev, second is track num
    MKV_CUR_DISC = QtCore.pyqtSignal(str, str)

    # First arg in dev, second is all info
    CD_ADD_DISC = QtCore.pyqtSignal(str, dict)
    # Arg is dev of disc to remove
    CD_REMOVE_DISC = QtCore.pyqtSignal(str)
    # First arg is dev, second is track num
    CD_CUR_TRACK = QtCore.pyqtSignal(str, str)
    # First arg is dev, second is size of cur track
    CD_TRACK_SIZE = QtCore.pyqtSignal(str, int)

    # dev of the rip to cancel
    CANCEL = QtCore.pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = logging.getLogger(__name__)
        self.enabled = False

        self.setWindowFlags(
            self.windowFlags()
            & ~QtCore.Qt.WindowCloseButtonHint
        )

        self.widgets = {}
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.MKV_ADD_DISC.connect(self.mkv_add_disc)
        self.MKV_REMOVE_DISC.connect(self.mkv_remove_disc)
        self.MKV_NEW_PROCESS.connect(self.mkv_new_process)
        self.MKV_CUR_TRACK.connect(self.mkv_current_track)

        self.CD_ADD_DISC.connect(self.cd_add_disc)
        self.CD_REMOVE_DISC.connect(self.cd_remove_disc)
        self.CD_CUR_TRACK.connect(self.cd_current_track)
        self.CD_TRACK_SIZE.connect(self.cd_track_size)

    def __len__(self):
        return len(self.widgets)

    @QtCore.pyqtSlot(str, dict, bool)
    def mkv_add_disc(self, dev: str, info: dict, full_disc: bool):
        self.log.debug("%s - Disc added", dev)
        widget = VideoProgressWidget(dev, info, full_disc)
        widget.CANCEL.connect(self.cancel)

        self.layout.addWidget(widget)
        self.widgets[dev] = widget
        self.show()
        self.adjustSize()

    @QtCore.pyqtSlot(str)
    def mkv_remove_disc(self, dev: str):
        widget = self.widgets.pop(dev, None)
        if widget is not None:
            self.layout.removeWidget(widget)
            widget.deleteLater()
            self.log.debug("%s - Disc removed", dev)

        if len(self.widgets) == 0:
            self.setVisible(False)
        self.adjustSize()

    @QtCore.pyqtSlot(str, Popen, str)
    def mkv_new_process(self, dev: str, proc: Popen, pipe: str):
        widget = self.widgets.get(dev, None)
        if widget is None:
            return
        self.log.debug("%s - Setting new parser process", dev)
        widget.NEW_PROCESS.emit(proc, pipe)

    @QtCore.pyqtSlot(str)
    def mkv_current_disc(self, dev: str):
        widget = self.widgets.get(dev, None)
        if widget is None:
            return

    @QtCore.pyqtSlot(str, str)
    def mkv_current_track(self, dev: str, title: str):
        widget = self.widgets.get(dev, None)
        if widget is None:
            return
        self.log.debug("%s - Setting current track: %s", dev, title)
        widget.current_track(title)

    @QtCore.pyqtSlot(str, dict)
    def cd_add_disc(self, dev: str, info: dict):
        self.log.debug("%s - Disc addeds", dev)
        widget = AudioProgressWidget(dev, info)
        widget.CANCEL.connect(self.cancel)

        self.layout.addWidget(widget)
        self.widgets[dev] = widget
        self.show()
        self.adjustSize()

    @QtCore.pyqtSlot(str)
    def cd_remove_disc(self, dev: str):
        widget = self.widgets.pop(dev, None)
        if widget is not None:
            self.layout.removeWidget(widget)
            widget.deleteLater()
            self.log.debug("%s - Disc removed", dev)
        if len(self.widgets) == 0:
            self.setVisible(False)
        self.adjustSize()

    @QtCore.pyqtSlot(str, str)
    def cd_current_track(self, dev: str, title: str):
        widget = self.widgets.get(dev, None)
        if widget is None:
            return
        self.log.debug("%s - Setting current track: %s", dev, title)
        widget.current_track(title)

    @QtCore.pyqtSlot(str, int)
    def cd_track_size(self, dev, tsize):
        widget = self.widgets.get(dev, None)
        if widget is None:
            return
        self.log.debug("%s - Update current track size: %d", dev, tsize)
        widget.track_size(tsize)

    @QtCore.pyqtSlot(str)
    def cancel(self, dev):
        self.CANCEL.emit(dev)
        self.MKV_REMOVE_DISC.emit(dev)
