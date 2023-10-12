import logging
import os
import shutil
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject
from core.gui.helpers import get_platform_name, absp, get_settings, replace_shortcut_link


class RomScannerWorkerSignals(QObject):
    romsListReady = pyqtSignal()
    changePage = pyqtSignal()
    romsRemoved = pyqtSignal()  # 삭제 작업을 알리기 위한 신호 추가
    rowsToRemove = pyqtSignal(list, str)  # 삭제완료 시그널
    showLoading = pyqtSignal()  # 로딩 오버레이 보여주기 위한 신호
    hideLoading = pyqtSignal()  # 로딩 오버레이 숨기기 위한 신호
    resourcesCopyCompleted = pyqtSignal(int)
    resourcesCopy = pyqtSignal(str, str, str)


class RomScannerWorker(QRunnable):
    def __init__(self, gui_behavior, action='scan', rows=[], text=''):
        super(RomScannerWorker, self).__init__()
        self.signals = RomScannerWorkerSignals()
        self.gui_behavior = gui_behavior
        self.action = action  # 작업 구분자: 'scan' 또는 'remove'
        self.rows = rows
        self.text = text

    def run(self):
        # 로딩 오버레이
        self.signals.showLoading.emit()

        if self.action == 'scan':
            # 롬 파일 목록 얻기
            self.gui_behavior.page = 1
            self.gui_behavior.get_files_list(action='scan')
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.signals.romsListReady.emit()
        elif self.action == 'next':
            # 다음 페이지로 이동
            if self.gui_behavior.page < self.gui_behavior.get_total_pages():
                self.gui_behavior.page += 1
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.changePage.emit()
        elif self.action == 'prev':
            # 이전 페이지로 이동
            if self.gui_behavior.page > 1:
                self.gui_behavior.page -= 1
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.changePage.emit()
        elif self.action == 'update':
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.romsListReady.emit()
        elif self.action == 'remove' or self.action == 'except':
            rows_to_remove = self.rows  # 여기에서 삭제하려는 행의 인덱스 목록을 생성합니다.
            self.signals.rowsToRemove.emit(rows_to_remove, self.action)
        elif self.action == 'copy':
            rows_to_remove = self.rows  # 여기에서 삭제하려는 행의 인덱스 목록을 생성합니다.
            self.signals.resourcesCopy.emit(self.gui_behavior.current_file_a_path,
                                            self.gui_behavior.current_file_b_path, self.gui_behavior.current_status)
        elif self.action == 'save':
            # 저장 폴더 경로
            directory3 = get_settings('directory3')

            folder_name = "output"  # 새로 생성하려는 폴더명
            new_folder_name = ""
            new_folder_path = os.path.normpath(
                os.path.join(directory3, folder_name))
            if not os.path.exists(new_folder_path):
                os.makedirs(new_folder_path)
            else:
                # 이미 폴더가 존재하면 숫자를 붙여서 새로운 폴더를 생성
                i = 1
                while True:
                    new_folder_name = f"{folder_name} ({i})"
                    new_folder_path = os.path.normpath(
                        os.path.join(directory3, new_folder_name))
                    if not os.path.exists(new_folder_path):
                        os.makedirs(new_folder_path)
                        break
                    i += 1

            work_cnt = 0

            for fileRow in self.gui_behavior.all_roms_list:
                # 파일 상태
                status = fileRow['status']
                current_path = ''
                if status in ('A', 'B', 'C'):
                    if status == 'A':
                        current_path = fileRow.get('file_a_path')
                    else:
                        status = 'B'  # A 가 아니면 모두 추가폴더 기준
                        current_path = fileRow.get('file_b_path')

                    file_path = os.path.normpath(current_path)

                    logging.debug(f'copy target path: {new_folder_path}')

                    self.gui_behavior.copy_file_to_target_folder_works(
                        file_path, new_folder_path, status)
                    work_cnt = work_cnt+1

            self.signals.resourcesCopyCompleted.emit(work_cnt)

        self.signals.hideLoading.emit()
