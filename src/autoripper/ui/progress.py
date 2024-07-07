from PyQt5 import QtCore

from automakemkv.ui import progress
from cdripper.ui.progress import ProgressWidget as AudioProgressWidget


class ProgressDialog(progress.ProgressDialog):

    @QtCore.pyqtSlot(str, dict)
    def add_disc(self, dev: str, info: dict):

        if 'isMovie' in info or 'isSeries' in info:
            self.log.debug("%s - Adding video disc", dev)
            widget = progress.ProgressWidget(dev, info)
        else:
            self.log.debug("%s - Adding audio disc", dev)
            widget = AudioProgressWidget(dev, info)
        widget.CANCEL.connect(self.cancel)

        self.layout.addWidget(widget)
        self.widgets[dev] = widget
        self.show()
        self.adjustSize()
