import logging
import sys
import os
import argparse

from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui

from cdripper import SETTINGS as AUDIO_SETTINGS
from automakemkv import SETTINGS as VIDEO_SETTINGS
from automakemkv.ui.dialogs import MissingDirDialog

from .. import LOG, STREAM, NAME, APP_ICON, TRAY_ICON
from ..watchdogs import linux
from . import progress
from . import dialogs
from . import utils


class SystemTray(QtWidgets.QSystemTrayIcon):
    """
    System tray class

    """

    def __init__(self, app, name=NAME):
        super().__init__(QtGui.QIcon(TRAY_ICON), app)
        self.setToolTip(NAME)

        self.__log = logging.getLogger(__name__)
        self._name = name
        self._settingsInfo = None
        self._app = app
        self._menu = QtWidgets.QMenu()

        self._label = QtWidgets.QAction(self._name)
        self._label.setEnabled(False)
        self._menu.addAction(self._label)

        self._menu.addSeparator()

        self._settings = QtWidgets.QAction('Settings')
        self._settings.triggered.connect(self.settings_widget)
        self._menu.addAction(self._settings)

        self._menu.addSeparator()

        self._quit = QtWidgets.QAction('Quit')
        self._quit.triggered.connect(self.quit)
        self._menu.addAction(self._quit)

        self.setContextMenu(self._menu)
        self.setVisible(True)

        self.progress = progress.ProgressDialog()
        self.ripper = linux.Watchdog(self.progress)
        self.ripper.start()

        # Set up check of output directory exists to run right after event
        # loop starts
        QtCore.QTimer.singleShot(
            0,
            self.check_outdir_exists,
        )

    def settings_widget(self, *args, **kwargs):

        self.__log.debug('opening settings')
        settings_widget = dialogs.SettingsDialog()
        if settings_widget.exec_():
            AUDIO_SETTINGS.save()
            VIDEO_SETTINGS.save()
        elif settings_widget.changed:
            AUDIO_SETTINGS.cancel()
            VIDEO_SETTINGS.cancel()

    def quit(self, *args, **kwargs):
        """Display quit confirm dialog"""
        self.__log.info('Saving settings')

        AUDIO_SETTINGS.save()
        VIDEO_SETTINGS.save()

        if kwargs.get('force', False):
            self.__log.info('Force quit')
            self.ripper.quit()
            self._app.quit()

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Are you sure you want to quit?")
        msg.setWindowTitle(f"{self._name} Quit")
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Yes
            | QtWidgets.QMessageBox.No
        )
        res = msg.exec_()
        if res == QtWidgets.QMessageBox.Yes:
            self.ripper.quit()
            self._app.quit()

    def check_outdir_exists(self):
        """
        Check that video/audio output directory exists

        """

        if not os.path.isdir(VIDEO_SETTINGS.outdir):
            dlg = MissingDirDialog(VIDEO_SETTINGS.outdir, 'Output')
            if not dlg.exec_():
                self.quit(force=True)
                return

            path = QtWidgets.QFileDialog.getExistingDirectory(
                QtWidgets.QDialog(),
                f'{self._name}: Select Video Output Folder',
            )
            if path != '':
                VIDEO_SETTINGS.update(outdir=path)
            self.check_outdir_exists()

        if not os.path.isdir(AUDIO_SETTINGS.outdir):
            dlg = MissingDirDialog(AUDIO_SETTINGS.outdir, 'Output')
            if not dlg.exec_():
                self.quit(force=True)
                return

            path = QtWidgets.QFileDialog.getExistingDirectory(
                QtWidgets.QDialog(),
                f'{self._name}: Select Audio Output Folder',
            )
            if path != '':
                AUDIO_SETTINGS.update(outdir=path)
            self.check_outdir_exists()


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loglevel',
        type=int,
        default=30,
        help='Set logging level',
    )

    args = parser.parse_args()

    STREAM.setLevel(args.loglevel)
    LOG.addHandler(STREAM)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(NAME)
    app.setWindowIcon(QtGui.QIcon(APP_ICON))
    app.setQuitOnLastWindowClosed(False)
    _ = SystemTray(app)
    app.exec_()
