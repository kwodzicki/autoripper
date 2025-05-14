from PyQt5 import QtWidgets
from PyQt5 import QtCore

from automakemkv.ui.dialogs import SettingsWidget as VideoSettingsWidget
from cdripper.ui.dialogs import SettingsWidget as AudioSettingsWidget

from . import utils


class SettingsDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tabs = QtWidgets.QTabWidget()
        self.video_widget = VideoSettingsWidget()
        self.audio_widget = AudioSettingsWidget()

        self.tabs.addTab(self.video_widget, 'Video')
        self.tabs.addTab(self.audio_widget, 'Audio')

        buttons = (
            QtWidgets.QDialogButtonBox.Save
            | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box = QtWidgets.QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.set_settings()

    def set_settings(self, settings: dict | None = None):

        if settings is None:
            settings = utils.load_settings()

        audio_outdir = settings.pop('audio_outdir', None)
        if audio_outdir is not None:
            self.audio_widget.set_settings(
                settings={'outdir': audio_outdir},
            )

        video_outdir = settings.pop('video_outdir', None)
        if video_outdir is not None:
            settings['outdir'] = video_outdir

        self.video_widget.set_settings(settings=settings)

    def get_settings(self):

        video_settings = self.video_widget.get_settings(save=False)
        audio_settings = self.audio_widget.get_settings(save=False)

        video_outdir = video_settings.pop('outdir', None)
        audio_outdir = audio_settings.pop('outdir', None)

        settings = {
            **video_settings,
            **audio_settings,
        }
        if video_outdir is not None:
            settings['video_outdir'] = video_outdir

        if audio_outdir is not None:
            settings['audio_outdir'] = audio_outdir

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
