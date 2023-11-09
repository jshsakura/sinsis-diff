import datetime
import filecmp
import hashlib
import os
import logging
import shutil

from PyQt5.QtCore import Qt, QThreadPool, QSize, QTimer
from PyQt5.QtGui import QColor
from core.gui.worker import RomScannerWorker
from .helpers import *
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QStandardItem, QImage, QIcon, QPixmap, QFont


class GuiBehavior:
    def __init__(self, gui):
        self.worker_thread = QThreadPool()
        self.worker_thread.setMaxThreadCount(1)
        self.process_workers = []
        self.gui = gui
        self.settings = None
        self.all_roms_list = []
        self.page = 1  # 현재 페이지 번호
        self.page_size = 1000  # 한 페이지에 표시할 아이템 수
        self.current_roms_list = []  # 현재 페이지의 롬 목록
        self.remove_roms_list = []  # 삭제할 롬 목록
        self.except_roms_list = []  # 삭제할 롬 목록
        self.msg_box = None
        self.current_file_a_path = None
        self.current_file_b_path = None
        self.current_status = None

    def get_current_page_roms(self):
        # 현재 페이지에 해당하는 롬 목록을 반환
        start_idx = (self.page - 1) * self.page_size
        end_idx = start_idx + self.page_size

        return self.all_roms_list[start_idx:end_idx]

    def next_page(self):
        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='next')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.changePage.connect(self.change_page_refresh)
        self.worker_thread.start(worker)

    def prev_page(self):
        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='prev')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.changePage.connect(self.change_page_refresh)
        self.worker_thread.start(worker)

    def get_total_pages(self):
        # 전체 페이지 수 계산
        return math.ceil(len(self.all_roms_list) / self.page_size)

    def handle_init(self):
        '''
        Load settings.
        Create file in case it doesn't exist.
        '''
        settings = []
        default_dir1 = get_settings('directory1')
        if default_dir1:
            self.gui.file_directory_input1.setText(default_dir1)
            settings.append(default_dir1)
        else:
            settings.append(None)

        default_dir2 = get_settings('directory2')
        if default_dir2:
            self.gui.file_directory_input2.setText(default_dir2)
            settings.append(default_dir2)
        else:
            settings.append(None)

        default_dir3 = get_settings('directory3')
        if default_dir3:
            self.gui.file_directory_input3.setText(default_dir3)
            settings.append(default_dir3)
        else:
            settings.append(None)

        except_ext = get_settings('except_ext')
        if except_ext:
            self.gui.file_directory_except_ext.setText(except_ext)
            settings.append(except_ext)
        else:
            settings.append(None)

        self.settings = settings

    def get_files_list(self, action):
        logging.debug('폴더 비교 작업 시작')
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        target_file_folder1 = get_settings('directory1')
        target_file_folder2 = get_settings('directory2')
        target_file_folder3 = get_settings('directory3')
        excluded_extensions = get_settings('except_ext')

        diff_list = self.compare_folders_recursively(
            target_file_folder1, target_file_folder2, excluded_extensions, hash_compare=True)

        if not diff_list:
            alert('설정하신 폴더의 경로의 파일이 모두 동일합니다.')

        self.all_roms_list = diff_list

    def calculate_file_hash(self, file_path, hash_algorithm='md5'):
        """파일의 해시 값을 계산하는 함수"""
        hash_obj = hashlib.new(hash_algorithm)
        with open(file_path, 'rb') as file:
            while True:
                data = file.read(1024*1024)  # 64 KB 씩 데이터를 읽습니다.
                if not data:
                    break
                hash_obj.update(data)
        return hash_obj.hexdigest()

    def should_skip_hash_compare(self, file_a_path, file_b_path):
        # Get the file sizes of file A and file B
        file_a_size = os.path.getsize(file_a_path)
        file_b_size = os.path.getsize(file_b_path)
        logging.debug(f'파일 A 크기: {file_a_size} B 크기: {file_b_size}')
        # Check if the file sizes are the same
        return file_a_size == file_b_size

    def compare_folders_recursively(self, folder_a, folder_b, excluded_extensions=None, hash_compare=True):
        if excluded_extensions is None:
            excluded_extensions = []

        diff_list = []

        for root, dirs, files in os.walk(folder_a):
            for file_a in files:
                file_a_path = os.path.normpath(os.path.join(root, file_a))
                relative_path = os.path.normpath(
                    os.path.relpath(file_a_path, folder_a))

                if any(relative_path.endswith(ext) for ext in excluded_extensions):
                    continue

                file_b_path = os.path.normpath(
                    os.path.join(folder_b, relative_path))

                # if not os.path.exists(file_b_path):
                # diff_list.append(
                #     self.get_row_item(file_a_path, file_b_path, "A"))
                # logging.debug(f'파일 A에만 존재: {file_a_path}')
                # el
                if os.path.exists(file_b_path) and hash_compare and self.should_skip_hash_compare(file_a_path, file_b_path):
                    hash_a = self.calculate_file_hash(file_a_path)
                    hash_b = self.calculate_file_hash(file_b_path)
                    if hash_a != hash_b:
                        diff_list.append(
                            self.get_row_item(file_a_path, file_b_path, "C"))
                        logging.debug(f'파일 내용이 다름: {file_a_path}')

        for root, dirs, files in os.walk(folder_b):
            for file_b in files:
                file_b_path = os.path.normpath(os.path.join(root, file_b))
                relative_path = os.path.normpath(
                    os.path.relpath(file_b_path, folder_b))

                if any(relative_path.endswith(ext) for ext in excluded_extensions):
                    continue

                file_a_path = os.path.normpath(os.path.normpath(
                    os.path.join(folder_a, relative_path)))

                if not os.path.exists(file_a_path):
                    diff_list.append(self.get_row_item(
                        file_a_path, file_b_path, "B"))
                    logging.debug(f'파일 B에만 존재: {file_b_path}')

        return diff_list

    def get_row_item(self, file_a_path, file_b_path, type):
        item = {}
        # logging.debug(
        #     f'<<<{file_a_path}>>> \n<<<{file_b_path}>>>')

        if type == "C":
            if file_a_path:
                file_a_byte = os.path.getsize(file_a_path)
                file_a_size = convert_size(file_a_byte)
                file_a_name = get_file_name_without_extension(file_a_path)
                file_a_time = os.path.getmtime(file_a_path)
                platform_a_name = get_platform_name(file_a_path)
            if file_b_path:
                file_b_byte = os.path.getsize(file_b_path)
                file_b_size = convert_size(file_b_byte)
                file_b_name = get_file_name_without_extension(file_b_path)
                file_b_time = os.path.getmtime(file_b_path)
                platform_b_name = get_platform_name(file_b_path)

        else:
            if type == "A":
                file_a_byte = os.path.getsize(file_a_path)
                file_a_size = convert_size(file_a_byte)
                file_a_name = get_file_name_without_extension(file_a_path)
                platform_a_name = get_platform_name(file_a_path)
                file_a_time = os.path.getmtime(file_a_path)
                file_b_byte = 0
                file_b_size = None
                file_b_name = None
                platform_b_name = None
                file_b_time = None
                logging.debug(file_a_size)
            else:
                file_a_byte = 0
                file_a_size = None
                file_a_name = None
                platform_a_name = None
                file_a_time = None
                file_b_byte = os.path.getsize(file_b_path)
                file_b_size = convert_size(file_b_byte)
                file_b_name = get_file_name_without_extension(file_b_path)
                platform_b_name = get_platform_name(file_b_path)
                file_b_time = os.path.getmtime(file_b_path)
                logging.debug(file_b_size)

        item = {"file_a_path": file_a_path, "file_a_size": file_a_size, "file_a_byte": file_a_byte,
                "file_a_name": file_a_name, "status": type, "file_a_platform_name": platform_a_name,
                "file_b_path": file_b_path, "file_b_size": file_b_size, "file_b_byte": file_b_byte,
                "file_b_name": file_b_name, "file_b_platform_name": platform_b_name,
                "status_name": "Hash 불일치" if type == "C" else ("A에만 존재" if type == "A" else "추가 파일"),
                "file_a_time": file_a_time, "file_b_time": file_b_time,
                "file_path": file_a_path if file_a_path else file_b_path,
                "platform_name": platform_a_name if platform_a_name else platform_b_name
                }
        return item

    def change_page_refresh(self):
        self.populate_table_with_roms()

        # 스크롤바 초기화
        self.gui.table.verticalScrollBar().setValue(0)

    def populate_table_with_roms(self):
        roms_list = self.get_current_page_roms()
        # 테이블을 비우고 진행
        self.gui.table_model.removeRows(0, self.gui.table_model.rowCount())

        italic_font = QFont(self.gui.font)
        italic_font.setItalic(True)

        for row, rom in enumerate(roms_list):
            # 행 높이 수정, 아이콘 사이즈 수정
            # self.gui.table.setRowHeight(row, 58)
            # self.gui.table.setIconSize(QSize(50, 58))

            # logging.debug(rom)
            platform_a_name = rom.get('file_a_platform_name', None)
            platform_b_name = rom.get('file_b_platform_name', None)
            platform_name = rom.get('platform_name', None)
            platform_a_icon = rom.get('file_a_platform_icon', None)
            platform_a_icon = rom.get('file_b_platform_icon', None)
            file_a_path = rom.get('file_a_path', None)
            file_b_path = rom.get('file_b_path', None)
            file_a_name = rom.get('file_a_name', None)
            file_b_name = rom.get('file_b_name', None)
            file_a_size = rom.get('file_a_size', None)
            file_b_size = rom.get('file_b_size', None)
            file_path = rom.get('file_path', None)
            thumbnail_a = None

            status = rom.get('status', None)
            status_name = rom.get('status_name', None)

            # 상태명 컬럼
            status_name_item = QStandardItem(status_name)
            status_name_item.setFlags(status_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            status_name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
            self.gui.table_model.setItem(row, 0, status_name_item)

            # 플랫폼(상위폴더) 설정
            platform_name_item = QStandardItem()
            platform_name_item.setText(platform_name)
            # 텍스트 좌측 정렬
            platform_name_item.setTextAlignment(
                Qt.AlignVCenter | Qt.AlignCenter)

            platform_name_item.setFlags(platform_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 1, platform_name_item)

            # 파일 경로 A 설정
            file_a_path_item = QStandardItem()
            file_a_path_item.setTextAlignment(
                Qt.AlignLeft | Qt.AlignVCenter)  # 텍스트를 왼쪽 정렬
            file_a_path_item.setData(
                Qt.ElideRight, Qt.DisplayRole)  # 텍스트 오버플로우 설정
            file_a_path_item.setSizeHint(
                QSize(file_a_path_item.sizeHint().width(), 2))
            file_a_path_item.setText(None if status == "B" else file_a_path)
            file_a_path_item.setFlags(file_a_path_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 2, file_a_path_item)
            self.gui.table.setColumnHidden(2, True)

            # 원본 파일명 설정
            file_a_name_item = QStandardItem(file_a_name)
            file_a_name_item.setFlags(file_a_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 3, file_a_name_item)
            self.gui.table.setColumnHidden(3, True)

            # 파일 수정 일시
            file_a_time_item = QStandardItem(
                self.get_file_mod_time(file_a_path))
            file_a_time_item.setFlags(file_a_time_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            file_a_time_item.setTextAlignment(
                Qt.AlignVCenter | Qt.AlignCenter)
            self.gui.table_model.setItem(row, 4, file_a_time_item)
            self.gui.table.setColumnHidden(4, True)

            # 파일 용량
            file_a_size_item = QStandardItem(file_a_size)
            file_a_size_item.setFlags(file_a_size_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            file_a_size_item.setTextAlignment(
                Qt.AlignVCenter | Qt.AlignRight)
            self.gui.table_model.setItem(row, 5, file_a_size_item)
            self.gui.table.setColumnHidden(5, True)

            # 단건 작업 버튼
            work_icon = None
            if status:
                icon_path = absp(f'res/icon/{status}.svg')
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
            self.gui.table_model.setItem(row, 6, file_work_item)

            # 파일 경로 B 설정
            file_b_path_item = QStandardItem()
            file_b_path_item.setTextAlignment(
                Qt.AlignLeft | Qt.AlignVCenter)  # 텍스트를 왼쪽 정렬
            file_b_path_item.setData(
                Qt.ElideRight, Qt.DisplayRole)  # 텍스트 오버플로우 설정
            file_b_path_item.setSizeHint(
                QSize(file_b_path_item.sizeHint().width(), 6))
            file_b_path_item.setText(None if status == "A" else file_b_path)
            file_b_path_item.setFlags(file_b_path_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 7, file_b_path_item)

            # 파일 수정 일시
            file_b_time_item = QStandardItem(
                self.get_file_mod_time(file_b_path))
            file_b_time_item.setFlags(file_b_time_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 8, file_b_time_item)
            file_b_time_item.setTextAlignment(
                Qt.AlignVCenter | Qt.AlignCenter)

            # 파일 용량
            file_b_size_item = QStandardItem(file_b_size)
            file_b_size_item.setFlags(file_b_size_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            file_b_size_item.setTextAlignment(
                Qt.AlignVCenter | Qt.AlignRight)
            self.gui.table_model.setItem(row, 9, file_b_size_item)

            # 추가 파일명 설정
            file_b_name_item = QStandardItem(file_b_name)
            file_b_name_item.setFlags(file_b_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 10, file_b_name_item)

            # 상태 컬럼
            status_item = QStandardItem(status)
            status_item.setFlags(status_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            status_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
            self.gui.table_model.setItem(row, 11, status_item)
            self.gui.table.setColumnHidden(11, True)

            # 상태 컬럼
            file_path_item = QStandardItem(file_path)
            file_path_item.setFlags(file_path_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            file_path_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
            self.gui.table_model.setItem(row, 12, file_path_item)
            self.gui.table.setColumnHidden(12, True)

            # 행 높이 수정, 아이콘 사이즈 수정
            # self.gui.table.setRowHeight(row, 58)
            # self.gui.table.setIconSize(QSize(50, 58))

        # 페이지 정보 업데이트 (예: "페이지 1 / 3")
        max_page = self.get_total_pages()
        if self.get_total_pages() > 0:
            self.gui.main.page_label.setText(
                f"페이지 {self.page} / {max_page}")

        # 페이지 버튼 활성 비활성
        if self.page == 1:
            self.gui.main.page_prev_btn.setDisabled(True)
            self.gui.main.page_next_btn.setDisabled(False)
        elif self.page == max_page:
            self.gui.main.page_prev_btn.setDisabled(False)
            self.gui.main.page_next_btn.setDisabled(True)
        else:
            self.gui.main.page_prev_btn.setDisabled(False)
            self.gui.main.page_next_btn.setDisabled(False)

        self.gui.update_titlebar()

    def set_save_output(self):
        # 롬 폴더 경로
        directory1 = get_settings('directory1')
        directory2 = get_settings('directory2')
        directory3 = get_settings('directory3')
        if not directory1 or not directory2 or not directory3:
            alert(
                '현재 설정하신 폴더 경로를 찾을 수 없습니다.\n먼저 설정 팝업에서 A,B 폴더의 위치를 지정해야합니다.')
            return

        if self.gui.table_model.rowCount() == 0:
            alert(
                '현재 화면의 조회 목록이 비어 있습니다.\n먼저 설정에서 폴더 경로를 지정하고 검색해야합니다.')
            return

        if not self.confirm_update_save():
            return

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='save')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.resourcesCopyCompleted.connect(
            self.set_save_output_file)
        self.worker_thread.start(worker)

    # 최종 파일 복사
    def set_save_output_file(self, work_cnt):
        self.show_save_completed_alert(work_cnt)
        # 일단 재조회
        worker = RomScannerWorker(self, action='scan')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.romsListReady.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def set_except(self):
        # 현재 선택된 행(ROMs)의 인덱스를 가져옵니다.
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            # 선택된 행이 없으면 경고 메시지를 표시하고 반환합니다.
            alert('목록에서 제외할 파일의 행을 선택하세요.')
            return

        if self.ask_for_delete_confirmation('except'):
            # 사용자가 '예'를 클릭한 경우, 행 삭제 작업을 진행합니다.
            worker = RomScannerWorker(
                self, action='except', rows=selected_rows)
            worker.signals.rowsToRemove.connect(
                self.remove_rows_from_table)  # 연결
            worker.signals.showLoading.connect(self.gui.show_loading_overlay)
            worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
            self.worker_thread.start(worker)
            pass

    def set_scan_file(self):
        logging.debug('파일 비교 시작')
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        target_file_folder = get_settings('directory1')
        if not target_file_folder:
            alert(
                '현재 설정된 폴더를 찾을 수 없습니다.\n먼저 설정에서 비교할 폴더 위치를 지정해주세요.')
            return

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='scan')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.romsListReady.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def show_save_completed_alert(self, work_cnt):
        if work_cnt == 0:
            alert('작업된 파일이 없습니다.')
        else:
            alert(f'output 폴더에 대상파일 {work_cnt} 건이 모두 복사되었습니다.')
            # self.set_scan_file()

    def confirm_update_save(self):
        message = "현재 목록의 A 폴더와 B 폴더의 차이가 있는 파일들을 \nB 폴더의 파일 기준으로 새로운 output 폴더에 복사합니다."
        reply = QMessageBox.question(None, '업데이트 outout 파일 저장', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def ask_for_delete_confirmation(self, action):
        # 선택된 행의 개수를 가져옵니다.
        selected_rows_count = len(
            self.gui.table.selectionModel().selectedRows())

        # 선택된 행이 없으면, 함수를 종료합니다.
        if selected_rows_count == 0:
            return False

        # 확인 메시지 박스 생성
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)

        action_name = ''
        if action == 'except':
            msg_box.setText(
                f"선택하신 {selected_rows_count}개의 행을 작업에서 제외하시겠습니까?")

        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # 사용자 응답 반환
        return msg_box.exec_() == QMessageBox.Yes

    def remove_rows_from_table(self, rows, action):
        for row in sorted(rows, reverse=True):  # 높은 인덱스부터 작업
            # 해당 행의 데이터 가져오기
            item_list = []
            for column in range(self.gui.table_model.columnCount()):
                item = self.gui.table_model.item(row, column)

                if column == 0:
                    new_text = '작업 제외'
                    font_color = QColor(255, 102, 102) if action == 'remove' else QColor(
                        255, 153, 0)
                    item.setText(new_text)
                    item.setForeground(font_color)

                    icon_path = absp('res/icon/alert-triangle.svg')
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
                    self.gui.table_model.setItem(row, 6, file_work_item)

                if item:
                    item_list.append(item.text())
                else:
                    item_list.append(None)

            # A또는 B의 파일경로를 사실상 키로 사용해도 무관
            file_path = item_list[7]

            if action == 'except':
                # 플랫폼 이름과 원본 파일명 가져오기
                self.remove_roms_list.append(item_list[7])  # 11은 파일 경로

            self.update_row_from_all_roms_list(file_path, action)

            # self.all_roms_list에서 해당 행 삭제
            # self.remove_row_from_all_roms_list(
            #     platform_name, original_filename)

            # 행 삭제
            # self.gui.table_model.removeRow(row)

    def update_row_from_all_roms_list(self, file_path, action):
        work_flag = False
        for index, rom in enumerate(self.all_roms_list):
            if rom['file_path'] == file_path:
                # 조건에 해당하는 항목을 찾았으므로 삭제합니다.
                if action == 'remove':
                    self.all_roms_list[index]['status'] = 'D'
                elif action == 'except':
                    self.all_roms_list[index]['status'] = 'E'
                break  # 해당 항목을 찾았으면 반복문 종료

    def get_selected_rows(self):
        # table_view는 QTableView의 인스턴스 이름입니다. 이를 적절하게 수정해야 합니다.
        selection_model = self.gui.table.selectionModel()
        selected_rows = selection_model.selectedRows()
        return [index.row() for index in selected_rows]

    def set_file_directory1(self):
        file_dialog = QFileDialog(self.gui.settings)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.exec_()
        self.gui.file_directory_input1.setText(file_dialog.selectedFiles()[0])

    def set_file_directory2(self):
        file_dialog = QFileDialog(self.gui.settings)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.exec_()
        self.gui.file_directory_input2.setText(file_dialog.selectedFiles()[0])

    def set_file_directory3(self):
        file_dialog = QFileDialog(self.gui.settings)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.exec_()
        self.gui.file_directory_input3.setText(file_dialog.selectedFiles()[0])

    def save_settings(self):
        settings = []
        if self.gui.file_directory_input1.text():
            set_settings('directory1',
                         self.gui.file_directory_input1.text())
            logging.debug('save_settings directory:' +
                          self.gui.file_directory_input1.text())
            settings.append(self.gui.file_directory_input1.text())
        else:
            set_settings('directory1', '')
            settings.append(None)

        if self.gui.file_directory_input2.text():
            set_settings('directory2',
                         self.gui.file_directory_input2.text())
            logging.debug('save_settings directory:' +
                          self.gui.file_directory_input2.text())
            settings.append(self.gui.file_directory_input2.text())
        else:
            set_settings('directory2', '')
            settings.append(None)

        if self.gui.file_directory_input3.text():
            set_settings('directory3',
                         self.gui.file_directory_input3.text())
            logging.debug('save_settings directory:' +
                          self.gui.file_directory_input3.text())
            settings.append(self.gui.file_directory_input3.text())
        else:
            set_settings('directory3', '')
            settings.append(None)

        if self.gui.file_directory_except_ext.text():
            set_settings('except_ext',
                         self.gui.file_directory_except_ext.text())
            logging.debug('save_settings except extension:' +
                          self.gui.file_directory_except_ext.text())
            settings.append(self.gui.file_directory_except_ext.text())
        else:
            set_settings('except_ext', '')
            settings.append(None)

        self.settings = settings
        self.gui.settings.hide()

    def select_settings(self):
        selection = self.gui.settings_list.selectedIndexes()[0].row()
        self.gui.stacked_settings.setCurrentIndex(selection)

    def handle_exit(self):
        # 종료시 동작 기술
        os._exit(1)

    def sort_all_roms_list(self, column, order):
        # self.all_roms_list를 정렬합니다.
        self.all_roms_list.sort(
            key=lambda rom: rom[column], reverse=(order == Qt.DescendingOrder))

        # 현재 페이지를 다시 그립니다.
        self.populate_table_with_roms()

    def get_file_mod_time(self, file_path, time_format='%Y-%m-%d %H:%M:%S'):
        """파일 수정일자를 지정된 형식으로 포맷하여 반환하는 함수"""
        if os.path.exists(file_path):
            modification_time = os.path.getmtime(file_path)
            formatted_time = datetime.datetime.fromtimestamp(
                modification_time).strftime(time_format)
            return formatted_time
        else:
            return None

    def copy_file_to_target_folder(self, file_a_path, file_b_path, status):
        logging.debug(f'파일A: {file_a_path}, 파일B:{file_b_path}, 상태: {status}')
        self.current_file_a_path = file_a_path if file_a_path else get_settings(
            'directory1')
        self.current_file_b_path = file_b_path if file_b_path else get_settings(
            'directory2')
        self.current_status = status

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='copy')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.resourcesCopy.connect(
            self.copy_file_to_target_folder_works)
        self.worker_thread.start(worker)

    def copy_file_to_target_folder_works(self, file_a_path, file_b_path, status, refresh=False):
        if status == "C":
            alert("두 파일의 Hash 값이 다릅니다.")
            return
        if not status in ["A", "B"]:
            return

        if not file_a_path or file_a_path == '':
            file_a_path = get_settings('directory1')
            logging.debug(f'A 경로가 지정되지 않았습니다. {file_a_path}')
        elif not file_b_path or file_b_path == '':
            file_b_path = get_settings('directory2')
            logging.debug(f'B 경로가 지정되지 않았습니다. {file_b_path}')

        source_path = ''
        source_folder = ''
        target_folder = ''

        # 대상 폴더 경로 설정
        if status == "A":
            source_path = file_a_path
            source_folder = get_settings('directory1')
            target_folder = file_b_path
        elif status == "B":
            source_path = file_b_path
            source_folder = get_settings('directory2')
            target_folder = file_a_path
        else:
            return  # 이외의 상태에 대한 처리가 필요할 수 있음

        # 동일한 폴더 구조로 복사
        logging.debug(
            f'소스경로: {source_path}, 소스폴더: {source_folder}, 타겟경로: {target_folder}')

        relative_path = os.path.relpath(source_path, source_folder)
        file_name = os.path.basename(source_path)
        logging.debug(f'소스경로: {relative_path}')

        target_path = os.path.normpath(
            os.path.join(target_folder, relative_path))
        target_dir = os.path.dirname(target_path)

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # 소스 파일과 대상 파일이 동일한 파일인지 확인
        if source_path != target_path:
            logging.debug(f'소스경로: {source_path}')
            logging.debug(f'타겟경로: {target_path}')

            shutil.copy2(source_path, target_path)

            if status == "A":
                folder_name = 'B' if file_b_path else 'output'
            elif status == "B":
                folder_name = 'A' if file_a_path else 'output'
            else:
                folder_name = 'output'  # 이외의 상태에 대한 처리가 필요할 수 있음

            logging.debug(
                f'{folder_name} 폴더로 복사 {source_path} -> {target_path}')
        else:
            logging.warning(f'소스 파일과 대상 파일이 동일합니다: {source_path}')

        if refresh:
            self.set_scan_file()
