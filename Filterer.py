"""
This is a little utility GUI application for searching
rows in a text file containing a search string and optionally saving
a new file containing only the rows with the search string.

The application will:

* load the lines of text from a text file
* filter rows based on an input string
* optionally save the rows of interest into a new file

Notes: need to use `io.open` instead of `codecs.open` to write filtered rows
because underlying encoded files are always opened in binary mode.
No automatic conversion of '\n' is done on reading and writing.
This is a problem for Notepad in Windows which doesn't recognize the new line.
"""
import sys
import io
import chardet

from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPlainTextEdit, QToolBar, QWidget, QPushButton,
                             QAction, QFileDialog, QApplication, QMessageBox,
                             QCheckBox, QLabel)

from PyQt5.QtCore import Qt

APP_USAGE_GUIDE = """
Usage guide
------------------------------------------------------------------
* Click File > Open (Ctrl-O) to open a text file. The filter edit
line will be focused automatically. The catalog path of the open
file will be shown on the toolbar.
* Enter the text and press the Enter key to filter. Click Ctrl-F
to focus the filter edit line if needed.
* Click File > Save (Ctrl-S) to save the filtered text lines into
a new file.
* Click File > Close (Ctrl-W) to close the file. Alternatively,
you can open a new file without closing the open one.

Notes:
------------------------------------------------------------------
* To make text smaller or larger, use the Zoom in/out buttons,
Ctrl+/Ctrl, or Ctrl-mousewheel.
* The application will save the output file in the same encoding
as the input file.
* The path to the open file can be selected with the mouse cursor.
"""


class MainWindow(QMainWindow):
    """Main entry point."""
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Filterer")
        self.setGeometry(100, 120, 0, 0)

        main_layout = QVBoxLayout()
        upper_layout = QHBoxLayout()
        lower_layout = QVBoxLayout()

        self.filter_button = QPushButton("Filter")
        self.filter_button.setDisabled(True)

        # checkbox
        self.do_live_search_checkbox = QCheckBox("Do live filtering", self)
        self.do_live_search_checkbox.setToolTip(
            "If enabled, "
            "the text will be filtered as you type")
        self.do_live_search_checkbox.setChecked(True)

        # open file path
        self.open_file_path_label = QLabel('')
        self.open_file_path_label.setToolTip("Use the mouse cursor to "
                                             "select and copy the path")
        self.open_file_path_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse)

        # items that user has searched for
        self.searched_items = []

        self.line_edit = QLineEdit()
        self.focus_line_edit = QAction("&Find", self)
        self.focus_line_edit.setShortcut("Ctrl+F")
        self.focus_line_edit.triggered.connect(
            lambda x: self.line_edit.setFocus())
        self.addAction(self.focus_line_edit)

        self.display = QPlainTextEdit()
        # no text data is loaded initially
        self.textfile_data = None

        # add text line to enter filter
        self.build_filter_line()
        self.handle_filtering_mode()

        # prepare display (main text block)
        self.build_display()

        # add widgets to layouts
        upper_layout.addWidget(self.line_edit)
        upper_layout.addWidget(self.filter_button)
        lower_layout.addWidget(self.display)

        # prepare app menu
        self.build_menu()

        # prepare the toolbar
        self.toolbar = QToolBar("My main toolbar")

        self.build_toolbar()

        # prepare the main layout of the whole application
        main_layout.addWidget(self.toolbar)
        main_layout.addLayout(upper_layout)
        main_layout.addLayout(lower_layout)

        margin = 10
        main_layout.setContentsMargins(margin, margin, margin, margin)

        # making the main layout the central widget of the application
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        # no file open yet, so encoding is unknown
        self.encoding = None

    def closeEvent(self, event):
        """Prompt user on exiting overriding the built-in closeEvent."""
        reply = QMessageBox.question(self, 'Exit application',
                                     "Do you really want to quit?",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def build_menu(self):
        """Build the main menu bar."""
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        menus = [("&Open", "Ctrl+O", self.open_file, False),
                 ("&Close", "Ctrl+W", self.close_file, True),
                 ("&Save as", "Ctrl+S", self.save_file, True),
                 ("&Quit", "Ctrl+Q", self.close, False)]

        for cmd_name, shortcut, connected_func, separator in menus:
            action = QAction(cmd_name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(connected_func)
            file_menu.addAction(action)
            if separator:
                file_menu.addSeparator()

        help_menu = menu.addMenu("&Help")
        action = QAction("&How to", self)
        action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(action)

    def show_help_dialog(self):
        """Show help dialog to explain how to use the app."""
        QMessageBox.about(self, "How to use the application", APP_USAGE_GUIDE)

    def build_toolbar(self):
        """Build the application toolbar."""
        self.addToolBar(self.toolbar)

        buttons = [("Zoom in", "Ctrl++", "Larger text (Ctrl++)",
                    lambda x: self.display.zoomIn(2)),
                   ("Zoom out", "Ctrl+-", "Smaller text (Ctrl+-)",
                    lambda x: self.display.zoomOut(2))]
        # add zoom in and zoom out buttons
        for cmd_name, shortcut, tooltip, connected_func in buttons:
            button_action = QPushButton(cmd_name, self)
            button_action.setShortcut(shortcut)
            button_action.setToolTip(tooltip)
            button_action.clicked.connect(connected_func)
            self.toolbar.addWidget(button_action)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.do_live_search_checkbox)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.open_file_path_label)

    def build_filter_line(self):
        """Build line edit to use input string as filter for the main display."""
        # initially disabled as no file has been loaded yet
        self.line_edit.setDisabled(True)
        self.line_edit.setPlaceholderText(
            "Enter the text to use as a filter...")
        self.line_edit.setToolTip(
            "Enter the text and press the "
            "Enter key to filter. Click Ctrl-F to focus.")

        # allow either press the Enter key to trigger filtering
        self.line_edit.returnPressed.connect(self.filter_button.click)
        self.do_live_search_checkbox.clicked.connect(
            self.handle_filtering_mode)

        # or clicking the Filter button
        self.filter_button.pressed.connect(self.filter_display)

    def handle_filtering_mode(self):
        """Handle filtering mode."""
        if self.do_live_search_checkbox.isChecked():
            self.line_edit.textChanged.connect(self.filter_button.click)
            self.filter_button.click()
        else:
            self.line_edit.textChanged.disconnect(self.filter_button.click)

    def build_display(self):
        """Build the display window (the main text block)."""
        # do not allow to make application window any smaller
        self.display.setMinimumHeight(300)
        self.display.setMinimumWidth(600)
        self.display.setLineWrapMode(False)

        # allow text to be selectable, but not editable
        self.display.setReadOnly(True)

        # initially will be disabled
        self.display.setDisabled(True)

        # setting a somewhat larger font size
        font = self.display.font()
        font.setPointSize(14)
        self.display.setFont(font)

    def filter_display(self):
        """Filter displayed text rows.
        Leave only those rows that have the entered string.
        This is triggered by clicking the Filter button.
        """
        filter_text_data = self.line_edit.text()

        # if user has not entered any string, the whole file is shown
        if not filter_text_data:
            self.display.setPlainText(''.join(self.textfile_data))
            return

        # otherwise only the rows with the string in them are shown
        self.display.setPlainText(''.join([
            i for i in self.textfile_data
            if filter_text_data.lower() in i.lower()
        ]))

    def open_file(self):
        """Open text file to load into the main display window."""
        name = QFileDialog.getOpenFileName(self, "Open text file")
        file_path = name[0]
        if file_path:
            self.encoding = self._detect_encoding(file_path)
            try:
                with io.open(file_path, encoding=self.encoding) as f:
                    self.textfile_data = f.readlines()
            except Exception:
                # if we failed to guess the encoding, fall back to UTF-8
                with io.open(file_path, encoding='utf-8') as f:
                    self.textfile_data = f.readlines()

            longest_textline = max([(i) for i in self.textfile_data], key=len)
            self.display.setPlainText("".join(self.textfile_data))

            if self.textfile_data:
                # file is not empty
                self.filter_button.setDisabled(False)
                self.line_edit.setDisabled(False)
                self.display.setDisabled(False)

                self.resize(
                    self.display.fontMetrics().width(longest_textline) + 50,
                    self.height())

                # let user start typing into the line edit immediately after loading
                self.line_edit.setFocus()

            else:
                self.filter_button.setDisabled(True)
                self.line_edit.setDisabled(True)

            self.open_file_path_label.setText(file_path.replace('/', '\\'))

    def save_file(self):
        """Save filtered text file into a new text file."""
        name = QFileDialog.getSaveFileName(self,
                                           "Save as new file",
                                           filter="All Files (*)")
        if name[0]:
            with io.open(name[0], "w", encoding=self.encoding) as f:
                text = self.display.toPlainText()
                f.write(text)
                f.close()

    def close_file(self):
        """Close the opened file. The text is removed and the tools are disabled."""
        self.line_edit.setText("")
        self.display.setPlainText("")
        self.filter_button.setDisabled(True)
        self.line_edit.setDisabled(True)
        self.display.setDisabled(True)

        self.open_file_path_label.setText('')

    @staticmethod
    def _detect_encoding(file_path):
        """Detect encoding of the input file."""
        with open(file_path, 'rb') as f:
            data = f.readline(1000)
            return chardet.detect(data)['encoding']


if __name__ == '__main__':
    APP = QApplication(sys.argv)

    WINDOW = MainWindow()
    WINDOW.show()

    sys.exit(APP.exec_())
