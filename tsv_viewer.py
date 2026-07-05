
from __future__ import annotations

import csv
import sys
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)


class TsvModel(QAbstractTableModel):
    """In-memory, read-only table model."""

    def __init__(self) -> None:
        super().__init__()
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self.search_text = ""

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        value = self.rows[index.row()][index.column()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return value
        if (
            role == Qt.ItemDataRole.BackgroundRole
            and self.search_text
            and self.search_text in value.casefold()
        ):
            return QColor("#fff09a")
        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def replace_data(self, headers: list[str], rows: list[list[str]]) -> None:
        self.beginResetModel()
        self.headers = headers
        self.rows = rows
        self.search_text = ""
        self.endResetModel()

    def set_search_text(self, text: str) -> None:
        new_text = text.casefold()
        if new_text == self.search_text:
            return
        self.search_text = new_text
        if self.rows and self.headers:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self.rows) - 1, len(self.headers) - 1),
                [Qt.ItemDataRole.BackgroundRole],
            )


def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Read a TSV, padding short rows so the result is rectangular."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            records = list(csv.reader(handle, delimiter="\t"))
    except UnicodeDecodeError:
        # A practical fallback for TSV files exported by older Windows software.
        with path.open("r", encoding="cp1252", newline="") as handle:
            records = list(csv.reader(handle, delimiter="\t"))

    if not records:
        return [], []

    width = max(len(row) for row in records)
    headers = records[0] + [f"Column {i + 1}" for i in range(len(records[0]), width)]
    rows = [row + [""] * (width - len(row)) for row in records[1:]]
    return headers, rows


class TsvViewer(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None
        self.matches: list[QModelIndex] = []
        self.match_position = -1
        self.model = TsvModel()

        self.setWindowTitle("TSV Viewer")
        self.resize(1100, 700)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)

        self.search_bar = QWidget()
        search_layout = QHBoxLayout(self.search_bar)
        search_layout.setContentsMargins(6, 4, 6, 4)
        search_layout.addWidget(QLabel("Find:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search all cells")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.update_search)
        self.search_input.returnPressed.connect(self.find_next)
        search_layout.addWidget(self.search_input, 1)

        previous_button = QPushButton("Previous")
        previous_button.clicked.connect(self.find_previous)
        search_layout.addWidget(previous_button)

        next_button = QPushButton("Next")
        next_button.clicked.connect(self.find_next)
        search_layout.addWidget(next_button)

        self.match_label = QLabel("")
        self.match_label.setMinimumWidth(90)
        search_layout.addWidget(self.match_label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.hide_search)
        search_layout.addWidget(close_button)
        self.search_bar.hide()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.search_bar)
        layout.addWidget(self.table, 1)
        self.setCentralWidget(container)

        self._create_actions()
        self.statusBar().showMessage("Open a TSV file to begin")

    def _create_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open TSV…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        find_action = QAction("&Find…", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.show_search)
        edit_menu.addAction(find_action)

        find_next_action = QAction("Find &Next", self)
        find_next_action.setShortcut(QKeySequence.StandardKey.FindNext)
        find_next_action.triggered.connect(self.find_next)
        edit_menu.addAction(find_next_action)

        find_previous_action = QAction("Find &Previous", self)
        find_previous_action.setShortcut(QKeySequence.StandardKey.FindPrevious)
        find_previous_action.triggered.connect(self.find_previous)
        edit_menu.addAction(find_previous_action)

    def choose_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open TSV file",
            str(self.current_path.parent if self.current_path else Path.home()),
            "TSV files (*.tsv *.tab);;Text files (*.txt);;All files (*)",
        )
        if filename:
            self.open_file(Path(filename))

    def open_file(self, path: Path) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            headers, rows = read_tsv(path)
        except (OSError, csv.Error) as error:
            QMessageBox.critical(self, "Could not open file", f"{path}\n\n{error}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.current_path = path
        self.model.replace_data(headers, rows)
        self.search_input.clear()
        self.matches = []
        self.match_position = -1
        self.setWindowTitle(f"{path.name} — TSV Viewer")
        self.statusBar().showMessage(
            f"{len(rows):,} rows × {len(headers):,} columns  |  {path}"
        )

    def show_search(self) -> None:
        self.search_bar.show()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def hide_search(self) -> None:
        self.search_input.clear()
        self.search_bar.hide()
        self.table.setFocus()

    def update_search(self, text: str) -> None:
        needle = text.casefold()
        self.model.set_search_text(text)
        self.matches = []
        self.match_position = -1

        if needle:
            for row_number, row in enumerate(self.model.rows):
                for column_number, value in enumerate(row):
                    if needle in value.casefold():
                        self.matches.append(self.model.index(row_number, column_number))

        if self.matches:
            self.match_position = 0
            self._show_current_match()
        elif needle:
            self.match_label.setText("No matches")
        else:
            self.match_label.clear()

    def find_next(self) -> None:
        if not self.matches:
            return
        self.match_position = (self.match_position + 1) % len(self.matches)
        self._show_current_match()

    def find_previous(self) -> None:
        if not self.matches:
            return
        self.match_position = (self.match_position - 1) % len(self.matches)
        self._show_current_match()

    def _show_current_match(self) -> None:
        index = self.matches[self.match_position]
        self.table.setCurrentIndex(index)
        self.table.scrollTo(index, QTableView.ScrollHint.PositionAtCenter)
        self.match_label.setText(f"{self.match_position + 1} of {len(self.matches)}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TSV Viewer")
    viewer = TsvViewer()
    viewer.show()

    if len(sys.argv) > 1:
        viewer.open_file(Path(sys.argv[1]).expanduser())

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
