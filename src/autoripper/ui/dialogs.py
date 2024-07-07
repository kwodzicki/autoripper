from PyQt5 import QtWidgets
from PyQt5 import QtCore

from automakemkv.ui.widgets import PathSelector

from . import utils


class SettingsWidget(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dbdir = PathSelector('autoMakeMKV Database Location:')
        self.video_outdir = PathSelector('Video Output Location:')
        self.audio_outdir = PathSelector('Audio Output Location:')

        radio_layout = QtWidgets.QVBoxLayout()
        self.features = QtWidgets.QRadioButton("Only Features")
        self.extras = QtWidgets.QRadioButton("Only Extras")
        self.everything = QtWidgets.QRadioButton("All Titles")
        radio_layout.addWidget(self.features)
        radio_layout.addWidget(self.extras)
        radio_layout.addWidget(self.everything)
        radio_widget = QtWidgets.QWidget()
        radio_widget.setLayout(radio_layout)

        self.set_settings()

        buttons = (
            QtWidgets.QDialogButtonBox.Save
            | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box = QtWidgets.QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.dbdir)
        layout.addWidget(self.video_outdir)
        layout.addWidget(self.audio_outdir)
        layout.addWidget(radio_widget)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def set_settings(self):

        settings = utils.load_settings()
        self.features.setChecked(True)
        if 'dbdir' in settings:
            self.dbdir.setText(settings['dbdir'])
        if 'video_outdir' in settings:
            self.video_outdir.setText(settings['video_outdir'])
        if 'audio_outdir' in settings:
            self.audio_outdir.setText(settings['audio_outdir'])
        if 'everything' in settings:
            self.everything.setChecked(settings['everything'])
        if 'extras' in settings:
            self.extras.setChecked(settings['extras'])

    def get_settings(self):

        settings = {
            'dbdir': self.dbdir.getText(),
            'video_outdir': self.video_outdir.getText(),
            'audio_outdir': self.audio_outdir.getText(),
            'extras': self.extras.isChecked(),
            'everything': self.everything.isChecked(),
        }
        utils.save_settings(settings)
        return settings


class MyQDialog(QtWidgets.QDialog):
    """
    Overload done() and new signal

    Create a new FINISHED signal that will pass bot the result code and
    the dev device. This signal is emitted in the overloaded done() method.

    """

    # The dev device and the result code
    FINISHED = QtCore.pyqtSignal(str, int)

    def done(self, arg):

        super().done(arg)
        self.FINISHED.emit(self.dev, self.result())
