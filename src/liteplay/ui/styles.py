"""Centralized application styling."""

APP_STYLESHEET = """
QWidget {
    color: #e2e6ec;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow, QWidget#appRoot, QStackedWidget#pageStack {
    background-color: #0e1116;
}

/* --- Sidebar --- */
QFrame#sidebar {
    background-color: #13171f;
    border-right: 1px solid #1f2532;
}

QLabel#brandLabel {
    color: #ffffff;
    font-size: 19px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#brandSubtitle {
    color: #636d7e;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#navButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #8c97a8;
    font-size: 13px;
    font-weight: 500;
    min-height: 34px;
    padding: 0 12px;
    text-align: left;
}

QPushButton#navButton:hover {
    background-color: #1a202c;
    color: #e2e8f0;
}

QPushButton#navButton:checked {
    background-color: #1e2638;
    border-color: #2b3954;
    color: #ffffff;
    font-weight: 600;
}

/* --- Common Typography --- */
QLabel#pageTitle {
    color: #ffffff;
    font-size: 22px;
    font-weight: 700;
}

QLabel#subtitle {
    color: #717d91;
    font-size: 13px;
}

QLabel#mutedText {
    color: #717d91;
    font-size: 12px;
}

QLabel#sectionTitle {
    color: #e2e8f0;
    font-size: 15px;
    font-weight: 600;
}

/* --- Primary / Action Buttons --- */
QPushButton#primaryButton {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    min-height: 30px;
    padding: 0 12px;
}

QPushButton#primaryButton:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton#primaryButton:pressed {
    background-color: #1e40af;
}

/* --- Library Search & Sort Controls --- */
QLineEdit#librarySearch {
    background-color: #13171f;
    border: 1px solid #283344;
    border-radius: 6px;
    color: #e2e8f0;
    min-height: 30px;
    padding: 0 22px 0 9px;
    font-size: 13px;
    placeholder-text-color: #64748b;
}

QLineEdit#librarySearch:hover {
    border-color: #3b4657;
}

QLineEdit#librarySearch:focus {
    background-color: #151b26;
    border-color: #3b82f6;
}

QComboBox#librarySort {
    background-color: #13171f;
    border: 1px solid #283344;
    border-radius: 6px;
    color: #dbe3ee;
    min-height: 30px;
    padding: 0 20px 0 9px;
    font-size: 13px;
}

QComboBox#librarySort:hover {
    border-color: #3b4657;
}

QComboBox#librarySort:focus {
    border-color: #3b82f6;
}

QComboBox#librarySort::drop-down {
    border: none;
    width: 22px;
}

QComboBox#librarySort QAbstractItemView {
    background-color: #13171f;
    border: 1px solid #283344;
    border-radius: 6px;
    color: #e2e8f0;
    selection-background-color: #20283a;
    selection-color: #7cb3ff;
    padding: 4px;
    outline: none;
}

QComboBox#librarySort QAbstractItemView::item {
    min-height: 26px;
    padding: 2px 8px;
    border-radius: 4px;
}

QComboBox#librarySort QAbstractItemView::item:hover {
    background-color: #1a202c;
    color: #ffffff;
}

QComboBox#librarySort QAbstractItemView::item:selected {
    background-color: #20283a;
    color: #7cb3ff;
}

/* --- Segmented View Selector --- */
QFrame#segmentedControl {
    background-color: #13171f;
    border: 1px solid #232a39;
    border-radius: 6px;
    padding: 2px;
}

QPushButton#segmentedButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: #8c97a8;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
    padding: 0 10px;
}

QPushButton#segmentedButton:hover {
    background-color: #1a202c;
    color: #e2e8f0;
}

QPushButton#segmentedButton:checked {
    background-color: #20283a;
    border-color: #2e3c57;
    color: #7cb3ff;
    font-weight: 600;
}

/* --- Cards and Containers --- */
QFrame#statCard, QFrame#sectionCard {
    background-color: #13171f;
    border: 1px solid #1f2532;
    border-radius: 8px;
}

QFrame#statCard:hover {
    background-color: #151a24;
    border-color: #263042;
}

QLabel#statLabel {
    color: #717d91;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#statValue {
    color: #ffffff;
    font-size: 22px;
    font-weight: 700;
}

/* --- Dashboard Preview Items --- */
QFrame#dashboardItem {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}

QFrame#dashboardItem:hover {
    background-color: #181d27;
    border-color: #242c3b;
}

QFrame#dashboardItem[running="true"] {
    background-color: #121c2a;
    border-color: #224268;
}

QFrame#dashboardItem[running="true"]:hover {
    background-color: #162438;
    border-color: #2d5585;
}

QLabel#dashboardGameName {
    color: #f1f5f9;
    font-size: 13px;
    font-weight: 600;
}

QLabel#dashboardMeta {
    color: #828fa3;
    font-size: 11px;
}

QLabel#dashboardMeta[running="true"] {
    color: #60a5fa;
    font-weight: 500;
}

/* --- Empty State --- */
QFrame#emptyState {
    background-color: #13171f;
    border: 1px dashed #273041;
    border-radius: 10px;
}

QLabel#emptyStateTitle {
    color: #f1f5f9;
    font-size: 16px;
    font-weight: 600;
}

QLabel#emptyStateText {
    color: #717d91;
    font-size: 13px;
}

QLabel#emptyStateStarIcon {
    color: #3b4657;
    font-size: 32px;
}

/* --- Scroll Area & Scrollbars --- */
QScrollArea#libraryScroll, QWidget#libraryContent {
    background: transparent;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #252d3d;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #354157;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #252d3d;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #354157;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* --- Game Row (Semi-list View) --- */
QFrame#gameRow {
    background-color: #13171f;
    border: 1px solid #1e2431;
    border-radius: 7px;
}

QFrame#gameRow:hover {
    background-color: #171d27;
    border-color: #2a3447;
}

QFrame#gameRow[running="true"] {
    background-color: #121a26;
    border: 1px solid #234873;
}

QFrame#gameRow[running="true"]:hover {
    background-color: #152233;
    border-color: #2f5d94;
}

/* --- Game Card (Grid View) --- */
QFrame#gameCard {
    background-color: #13171f;
    border: 1px solid #1e2431;
    border-radius: 8px;
}

QFrame#gameCard:hover {
    background-color: #171d27;
    border-color: #2a3447;
}

QFrame#gameCard[running="true"] {
    background-color: #121a26;
    border: 1px solid #234873;
}

QFrame#gameCard[running="true"]:hover {
    background-color: #152233;
    border-color: #2f5d94;
}

QLabel#gameName {
    color: #f1f5f9;
    font-size: 14px;
    font-weight: 600;
}

QLabel#gameMeta {
    color: #94a3b8;
    font-size: 12px;
}

/* --- Game Actions --- */
QPushButton#launchButton {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
    min-height: 24px;
    padding: 0 10px;
}

QPushButton#launchButton:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton#launchButton:pressed {
    background-color: #1e40af;
    border-color: #2563eb;
}

QPushButton#launchButton:disabled {
    background-color: #122135;
    border-color: #1e3d61;
    color: #72b2f5;
}

QPushButton#favoriteButton {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    color: #64748b;
    font-size: 14px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
}

QPushButton#favoriteButton:hover {
    background-color: #1c2331;
    color: #f59e0b;
}

QPushButton#favoriteButton[active="true"] {
    color: #f59e0b;
}

QPushButton#favoriteButton[active="true"]:hover {
    background-color: #242d3f;
    color: #fbbf24;
}

QPushButton#removeButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: #788598;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
    padding: 0 8px;
}

QPushButton#removeButton:hover {
    background-color: #212028;
    border-color: #38303a;
    color: #e2848c;
}

QPushButton#removeButton:pressed {
    background-color: #282028;
    border-color: #483440;
    color: #ef5350;
}

QPushButton#removeButton:disabled {
    background-color: transparent;
    border-color: transparent;
    color: #3e4856;
}

QPushButton#editButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: #8f9caf;
    font-size: 12px;
    font-weight: 500;
    min-height: 24px;
    padding: 0 7px;
}

QPushButton#editButton:hover {
    background-color: #1c2331;
    border-color: #303b50;
    color: #dbeafe;
}

QPushButton#editButton:disabled {
    color: #3e4856;
}
"""
