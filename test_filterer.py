from unittest.mock import patch

from PyQt5.Qt import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QMessageBox

from Filterer import MainWindow


def test_app(qtbot, tmp_path):
    ui = MainWindow()
    ui.show()
    QTest.qWaitForWindowExposed(ui)

    datafile = tmp_path.joinpath("population.csv")
    subsetfile = tmp_path.joinpath("population_subset.csv")

    with open(datafile, "w") as fh:
        for row in [["City", "Year", "Population"], ["City1", "1800", "1000"],
                    ["City1", "1900", "10000"], ["City2", "1800", "2000"],
                    ["City2", "1900", "20000"], ["City3", "1800", "3000"],
                    ["City3", "1900", "30000"], ["City4", "1800", "4000"],
                    ["City4", "1900", "40000"]]:
            fh.write(','.join(row) + "\n")

    with patch('Filterer.QFileDialog.getOpenFileName',
               lambda *args: [datafile.as_posix()]):
        QTest.keyPress(ui, Qt.Key_O, Qt.ControlModifier)
        assert ui.textfile_data

    ui.line_edit.setText("City1")
    ui.filter_display()
    assert len(ui.display.toPlainText().split('\n')) == 3

    with patch('Filterer.QFileDialog.getSaveFileName',
               lambda *args, **kwargs: [subsetfile.as_posix()]):
        QTest.keyPress(ui, Qt.Key_S, Qt.ControlModifier)
        assert subsetfile.read_text().split() == [
            'City1,1800,1000', 'City1,1900,10000'
        ]

    QTest.keyPress(ui, Qt.Key_W, Qt.ControlModifier)
    assert ui.display.toPlainText() == ''

    with patch('Filterer.QMessageBox.question', lambda *args: QMessageBox.Yes):
        QTest.keyPress(ui, Qt.Key_Q, Qt.ControlModifier)
