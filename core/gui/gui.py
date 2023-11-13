import math
import os
import sys
import logging
import time
import webbrowser
import qdarktheme
import subprocess
import platform
from .behavior import GuiBehavior
from PyQt5.QtCore import Qt, QObject, QEvent, QSize
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtGui import QIcon, QStandardItemModel, QPixmap, QFontDatabase, QFont, QColor, QCursor, QStandardItem
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGridLayout, QPushButton,  QWidget,
                             QTableView,  QHBoxLayout, QVBoxLayout, QAbstractItemView, QMenu, QAction,
                             QAbstractScrollArea, QLabel, QLineEdit, QStackedWidget, QMessageBox, QTextEdit,
                             QFormLayout, QListWidget, QComboBox, QSizePolicy, QHeaderView, QHeaderView, QStyledItemDelegate)
from .helpers import *


class Gui:
    def __init__(self):
        # Init GuiBehavior()
        self.app_name = 'Sinsis Diff'
        self.font = None
        self.table_model = None
        self.msg_box = None

        # Init DB
        database_init()

        # Create App
        qdarktheme.enable_hi_dpi()
        app = QApplication(sys.argv)
        qdarktheme.setup_theme("light")

        font_database = QFontDatabase()
        font_id = font_database.addApplicationFont(
            absp("res/fonts/NanumGothic.ttf"))
        if font_id == -1:
            logging.debug("Font load failed!")
        else:
            font_families = font_database.applicationFontFamilies(font_id)
            self.font = QFont(font_families[0], 9)

        app.setWindowIcon(QIcon(absp('res/icon/ico.ico')))
        app.setStyle('Fusion')
        self.app = app

        # Initialize self.main
        self.main_init()
        self.actions = GuiBehavior(self)
        app.aboutToQuit.connect(self.actions.handle_exit)

        # Create Windows
        self.main_win()
        self.settings_win()
        self.actions.handle_init()

        # 셀 편집 완료 시 이벤트 연결
        self.table_model.itemChanged.connect(self.handle_item_changed)
        # Connect the model signals to update the status bar
        self.table_model.rowsInserted.connect(self.update_titlebar)
        self.table_model.rowsRemoved.connect(self.update_titlebar)

        sys.exit(app.exec_())

    def update_titlebar(self):
        count = len(self.actions.all_roms_list)
        title_text = f"{self.app_name} [ 비교 대상 파일 수: {count} ]"

        self.main.setWindowTitle(title_text)

    def main_init(self):
        # Define Main Window
        self.main = QMainWindow()
        self.main.setWindowTitle(self.app_name)
        self.main.setFont(self.font)

        widget = QWidget(self.main)
        self.main.setCentralWidget(widget)

        # Create Grid
        grid = QGridLayout()

        # Table
        self.table = QTableView()

        headers = ['상태', '상위 폴더', '파일 경로', '기준 파일 이름', '수정 일시', '파일 용량', '',
                   '파일 경로', '수정 일시', '파일 용량', '파일 이름']
        self.table.setSizeAdjustPolicy(
            QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # 선택 동작 설정 (SelectRows를 사용하여 행 전체를 선택)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSortingEnabled(True)

        # 마우스 이벤트 처리 함수 연결
        self.table.entered.connect(self.setCursorToHand)

        # 헤더 클릭 이벤트 핸들러 설정
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.table.verticalHeader().hide()

        # 테이블 간격 조정
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(headers)

        # 헤더의 폰트 크기 설정
        header = self.table.horizontalHeader()
        header_font = self.font
        header.setFont(header_font)
        header.setFixedHeight(23)
        header.setHighlightSections(False)

        self.table.setModel(self.table_model)

        # 폰트 변경
        if self.font:
            self.table.setFont(self.font)

        # 컬럼 사이즈 조절
        self.table.setColumnWidth(0, 85)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(6, 25)
        self.table.setColumnWidth(7, 90)
        self.table.setColumnWidth(8, 140)
        self.table.setColumnWidth(9, 80)

        # 컬럼 숨김
        self.table.setColumnHidden(2, True)
        self.table.setColumnHidden(3, True)
        self.table.setColumnHidden(4, True)
        self.table.setColumnHidden(5, True)

        # '원본 파일명' 열을 오름차순으로 정렬합니다.
        self.table.sortByColumn(0, Qt.AscendingOrder)
        # 기본 sort 버튼 숨김
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self.table.setSortingEnabled(False)
        # 클릭 이벤트 핸들러 연결
        self.table.clicked.connect(self.on_cell_clicked)

        # Add buttons to Horizontal Layout
        hbox = QHBoxLayout()
        # Bottom Buttons
        self.main.settings_btn = QPushButton(
            QIcon(absp('res/icon/settings.svg')), ' 설정')
        self.main.settings_btn.clicked.connect(lambda: self.settings.show(
        ) if not self.settings.isVisible() else self.settings.raise_())

        self.main.scan_btn = QPushButton(
            QIcon(absp('res/icon/refresh-cw.svg')), ' 파일 비교')

        self.main.except_btn = QPushButton(
            QIcon(absp('res/icon/file-minus.svg')), ' 작업 제외')

        self.main.save_btn = QPushButton(
            QIcon(absp('res/icon/save.svg')), ' 업데이트 저장')

        large_font = QFont(self.font)
        large_font.setPointSize(10)

        self.main.settings_btn.setFont(large_font)
        self.main.scan_btn.setFont(large_font)
        self.main.except_btn.setFont(large_font)
        self.main.save_btn.setFont(large_font)

        self.main.settings_btn.setStyleSheet("color: #333333;")
        self.main.scan_btn.setStyleSheet("color: #333333;")
        self.main.except_btn.setStyleSheet("color: #333333;")
        self.main.save_btn.setStyleSheet("color: #333333;")

        self.main.page_label = QLabel()
        self.main.page_prev_btn = QPushButton()
        self.main.page_next_btn = QPushButton()

        # 버튼 아이콘 설정
        self.main.page_prev_btn.setIcon(
            QIcon(absp('res/icon/chevron-left.svg')))
        self.main.page_next_btn.setIcon(
            QIcon(absp('res/icon/chevron-right.svg')))

        self.main.page_label.setFont(self.font)
        self.main.page_prev_btn.setFont(self.font)
        self.main.page_next_btn.setFont(self.font)
        self.main.page_prev_btn.setEnabled(False)
        self.main.page_next_btn.setEnabled(False)
        self.main.page_prev_btn.setStyleSheet("color: #333333;")
        self.main.page_next_btn.setStyleSheet("color: #333333;")

        # 모든 버튼에 대해 커서 설정
        for button in [self.main.page_prev_btn, self.main.page_next_btn, self.main.settings_btn, self.main.scan_btn, self.main.except_btn, self.main.save_btn]:
            button.setCursor(Qt.PointingHandCursor)

        # 페이징 라벨 추가
        self.main.page_label.setAlignment(Qt.AlignCenter)

        # 아래에 페이지 관련 위젯을 추가
        button_container = QWidget(self.main)
        button_layout = QGridLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.main.page_prev_btn, 1, 0)
        button_layout.addWidget(self.main.page_next_btn, 1, 1)

        # self.log_textedit = QTextEdit(self.main)
        # self.log_textedit.setReadOnly(True)
        # self.log_textedit.setFixedHeight(150)  # 높이를 200 픽셀로 설정
        # # Set up logging
        # logging.basicConfig(
        #     level=logging.DEBUG,
        #     format='%(asctime)s - %(levelname)s - %(message)s',
        #     handlers=[QtHandler(self.log_textedit.append)]
        # )

        # 그리드 먼저 추가
        grid.addWidget(self.table, 1, 0, 1, 7)
        # 로그 텍스트 추가
        # grid.addWidget(self.log_textedit, 2, 0, 1, 7)
        # 하단 버튼 추가
        grid.addWidget(self.main.settings_btn, 3, 0)
        grid.addWidget(self.main.scan_btn, 3, 1)
        grid.addWidget(self.main.except_btn, 3, 2)
        grid.addWidget(self.main.save_btn, 3, 3)
        grid.addWidget(self.main.page_label, 3, 5)
        grid.addWidget(button_container, 3, 6)

        self.main.setWindowFlags(self.main.windowFlags()
                                 & Qt.CustomizeWindowHint)

        widget.setLayout(grid)
        self.main.resize(700, 514)
        # Set size policies for the table
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 로딩 오버레이 위젯 생성
        self.main.loading_overlay = LoadingOverlay(self.main)
        # LoadingOverlay 클래스를 부모 위젯에 추가한 후 이벤트 필터를 설치
        # self.main.setCentralWidget(widget)
        self.main.installEventFilter(self.main.loading_overlay)

        self.main.show()

    # 특정 셀 위에 마우스를 올렸을 때 커서 모양 설정
    def setCursorToHand(self, index):
        if index.column() == 3 or index.column() == 6 or index.column() == 7:
            model = self.table.model()  # 테이블의 모델 가져오기
            row = index.row()
            column = index.column()

            if column == 6:
                status = self.table_model.item(row, 11).text()
                if status in ["A", "B", "C"]:
                    self.table.setCursor(QCursor(Qt.PointingHandCursor))
            else:
                cell_text = model.data(index, Qt.DisplayRole)  # 해당 셀의 데이터 가져오기
                if cell_text.strip():
                    self.table.setCursor(QCursor(Qt.PointingHandCursor))
                else:
                    self.table.setCursor(QCursor(Qt.ArrowCursor))
        else:
            self.table.setCursor(QCursor(Qt.ArrowCursor))

    def main_win(self):
        self.main.scan_btn.clicked.connect(self.actions.set_scan_file)
        self.main.except_btn.clicked.connect(self.actions.set_except)
        self.main.save_btn.clicked.connect(self.actions.set_save_output)
        # 페이지 이전/다음 버튼 클릭 시 해당 함수 연결
        self.main.page_prev_btn.clicked.connect(self.actions.prev_page)
        self.main.page_next_btn.clicked.connect(self.actions.next_page)

        self.table.setMouseTracking(True)

    # 로딩 오버레이를 활성화하는 메서드
    def show_loading_overlay(self):
        if self.main:
            self.main.loading_overlay.show()
            self.main.settings_btn.setEnabled(False)
            self.main.scan_btn.setEnabled(False)
            self.main.except_btn.setEnabled(False)
            self.main.save_btn.setEnabled(False)
            self.main.page_prev_btn.setEnabled(False)
            self.main.page_next_btn.setEnabled(False)

    # 로딩 오버레이를 비활성화하는 메서드
    def hide_loading_overlay(self):
        if self.main:
            self.main.loading_overlay.hide()
            self.main.settings_btn.setEnabled(True)
            self.main.scan_btn.setEnabled(True)
            self.main.except_btn.setEnabled(True)
            self.main.save_btn.setEnabled(True)

    def settings_win(self):
        # Define Settings Win
        self.settings = QMainWindow(self.main)
        self.settings.setWindowTitle('설정')

        # Create StackedWidget and Selection List
        self.stacked_settings = QStackedWidget()
        self.settings_list = QListWidget()
        self.settings_list.setFixedWidth(100)
        self.settings_list.addItems(['기본 설정', '프로그램 정보'])
        self.settings_list.clicked.connect(self.actions.select_settings)
        self.settings_list.setCurrentRow(0)

        # Central Widget
        central_widget = QWidget()
        hbox = QHBoxLayout()
        hbox.addWidget(self.settings_list)

        hbox.addWidget(self.stacked_settings)
        central_widget.setLayout(hbox)
        self.settings.setCentralWidget(central_widget)

        behavior_settings = QWidget()
        self.stacked_settings.addWidget(behavior_settings)

        # Main Layouts
        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignTop)
        form_layout = QFormLayout()

        form_layout.addRow(QLabel('작업시 제외할 확장자 (,콤마로 입력)'))
        self.file_directory_except_ext = QLineEdit()
        if self.actions.settings is not None:
            self.file_directory_except_ext.setText(self.actions.settings[3])
            self.file_directory_except_ext.repaint()

        form_layout.addRow(self.file_directory_except_ext)

        # Folder Directory 1
        form_layout.addRow(QLabel('기준 A 폴더 경로를 선택합니다.'))

        file_directory_btn1 = QPushButton('폴더 선택..')
        file_directory_btn1.clicked.connect(self.actions.set_file_directory1)

        self.file_directory_input1 = QLineEdit()
        if self.actions.settings is not None:
            self.file_directory_input1.setText(self.actions.settings[0])
            self.file_directory_input1.repaint()
        self.file_directory_input1.setReadOnly(True)

        form_layout.addRow(file_directory_btn1, self.file_directory_input1)
        form_layout.addRow(QLabel('추가 B 폴더 경로를 선택합니다.'))

        file_directory_btn2 = QPushButton('폴더 선택..')
        file_directory_btn2.clicked.connect(self.actions.set_file_directory2)

        self.file_directory_input2 = QLineEdit()
        if self.actions.settings is not None:
            self.file_directory_input2.setText(self.actions.settings[1])
            self.file_directory_input2.repaint()
        self.file_directory_input2.setReadOnly(True)

        form_layout.addRow(file_directory_btn2, self.file_directory_input2)

        form_layout.addRow(QLabel('저장 경로 (output 폴더 자동 생성)'))
        file_directory_btn3 = QPushButton('경로 선택..')
        file_directory_btn3.clicked.connect(self.actions.set_file_directory3)

        self.file_directory_input3 = QLineEdit()
        if self.actions.settings is not None:
            self.file_directory_input3.setText(self.actions.settings[2])
            self.file_directory_input3.repaint()
        self.file_directory_input3.setReadOnly(True)

        form_layout.addRow(file_directory_btn3, self.file_directory_input3)

        # Bottom Buttons
        save_settings = QPushButton('설정 저장')
        save_settings.clicked.connect(self.actions.save_settings)

        vbox.addLayout(form_layout)
        vbox.addStretch()
        vbox.addWidget(save_settings)
        behavior_settings.setLayout(vbox)

        '''
        Child widget
        About
        '''

        about_settings = QWidget()
        self.stacked_settings.addWidget(about_settings)

        about_layout = QGridLayout()
        about_layout.setAlignment(Qt.AlignCenter)

        logo = QLabel()
        logo.setPixmap(QPixmap(absp('res/icon/ico.svg')))
        logo.setAlignment(Qt.AlignCenter)

        text = QLabel(self.app_name)
        text.setStyleSheet('font-weight: bold; color: #4256AD')

        github_btn = QPushButton(QIcon(absp('res/icon/github.svg')), '')
        github_btn.setFixedWidth(32)
        github_btn.clicked.connect(lambda: webbrowser.open(
            'https://github.com/jshsakura/sinsis-diff'))

        about_layout.addWidget(logo, 0, 0, 1, 0)
        about_layout.addWidget(github_btn, 1, 0)
        about_layout.addWidget(text, 1, 1)
        about_settings.setLayout(about_layout)

    def on_cell_clicked(self, index):
        row = index.row()
        column = index.column()
        if column == 2:
            # 셀의 내용을 가져옵니다.
            file_path = self.table_model.item(row, 2).text()
            if file_path:
                self.open_in_explorer(file_path)
        elif column == 7:
            # 셀의 내용을 가져옵니다.
            file_path = self.table_model.item(row, 7).text()
            if file_path:
                self.open_in_explorer(file_path)
        elif column == 6:
            # 셀의 내용을 가져옵니다.
            icon = self.table_model.item(row, 6)
            status = self.table_model.item(row, 11).text()
            file_a_path = self.table_model.item(row, 2).text()
            file_b_path = self.table_model.item(row, 7).text()

            if status in ['E']:
                return
            if status == 'C':
                self.actions.copy_file_to_target_folder(
                    file_a_path, file_b_path, status)
                return
            if icon and status:
                self.actions.copy_file_to_target_folder(
                    file_a_path, file_b_path, status)
                # 목록에서 예외처리
                self.actions.update_row_from_all_roms_list(
                    file_b_path, 'except')
                self.actions.remove_roms_list.append(file_b_path)
                self.table_model.item(row, 0).setText('파일 복사')
                self.table_model.item(row, 0).setForeground(
                    QColor(0, 204, 153))
                self.table_model.item(row, 11).setText('E')

                icon_path = absp('res/icon/check-square.svg')
                icon = QIcon(icon_path)
                size = QSize(32, 32)
                pixmap = icon.pixmap(size)
                work_icon = QIcon(pixmap)
                file_work_item = QStandardItem()
                file_work_item.setIcon(work_icon)
                file_work_item.setFlags(file_work_item.flags(
                ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                file_work_item.setTextAlignment(
                    Qt.AlignVCenter | Qt.AlignCenter)
                self.table_model.setItem(row, 6, file_work_item)

    def open_in_explorer(self, file_path):
        folder_path = os.path.dirname(file_path)  # 파일의 폴더 경로를 얻습니다.
        # OS에 따라 명령어를 다르게 실행합니다.
        if platform.system() == 'Windows':
            # 파일을 강조 표시하려면 /select 옵션을 사용합니다.
            subprocess.Popen(f'explorer /select,"{file_path}"')
        elif platform.system() == 'Darwin':  # macOS의 경우
            subprocess.Popen(['open', folder_path])
        elif platform.system() == 'Linux':
            subprocess.Popen(['xdg-open', folder_path])

    def on_header_clicked(self, logical_index):
        # 헤더 클릭 시 호출되는 함수
        order = self.table.horizontalHeader().sortIndicatorOrder()

        # column 변수를 어떻게 정의했는지에 따라 정렬합니다.
        column = {0: "status", 1: "platform_name", 2: "file_a_path", 3: "file_a_name", 4: 'file_a_time', 5: 'file_a_byte', 6: "status",
                  7: "file_b_path", 8: "file_b_time", 9: 'file_b_byte', 10: 'file_b_name'}

        # 정렬 불가능한 열은 볼 것도 없음
        if not logical_index in column:
            self.table.horizontalHeader().setSortIndicatorShown(False)
            self.table.setSortingEnabled(False)
            return
        else:
            self.table.horizontalHeader().setSortIndicatorShown(True)
            self.table.setSortingEnabled(True)

        if self.actions:
            self.actions.all_roms_list.sort(key=lambda rom: (
                rom[column[logical_index]] is None, rom[column[logical_index]]), reverse=(order == Qt.DescendingOrder))

            # 현재 페이지를 다시 그립니다.
            self.actions.populate_table_with_roms()

            # 정렬 방향을 토글하며 해당 열을 소팅합니다.
            if order == Qt.AscendingOrder:
                self.table.sortByColumn(logical_index, Qt.DescendingOrder)
                self.table.horizontalHeader().setSortIndicator(logical_index, Qt.AscendingOrder)
            else:
                self.table.sortByColumn(logical_index, Qt.AscendingOrder)
                self.table.horizontalHeader().setSortIndicator(logical_index, Qt.DescendingOrder)

    def handle_item_changed(self, item):
        # 아이템이 속한 모델을 가져옵니다.
        # 변경된 아이템의 행과 열 번호를 얻습니다.
        row = item.row()
        column = item.column()
        # 셀의 값이 변경되면 호출되는 메서드

        if column == 0:
            status = item.model().item(row, 0).text()
            print(status)


class QtHandler(logging.Handler):
    def __init__(self, log_append_function):
        super().__init__()
        self.log_append_function = log_append_function

    def emit(self, record):
        log_message = self.format(record)
        self.log_append_function(log_message)


class LoadingOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        self.setWindowFlags(Qt.FramelessWindowHint)
        # SVG 이미지를 로딩 오버레이 위젯에 추가
        svg_widget = QSvgWidget(absp('res/icon/loading_image.svg'))
        svg_widget.setGeometry(0, 0, 100, 100)  # 중앙에 표시하려면 위치와 크기 조정이 필요합니다.
        svg_layout = QVBoxLayout(self)
        svg_layout.addWidget(svg_widget)
        svg_layout.setAlignment(Qt.AlignCenter)
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.resize(parent.size())
        self.hide()

    def resizeEvent(self, event):
        # 오버레이의 지오메트리를 부모 위젯의 크기와 일치하도록 업데이트합니다.
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
