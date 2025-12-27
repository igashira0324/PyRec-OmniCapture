from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QCheckBox, QGroupBox, 
                             QFileDialog, QSystemTrayIcon, QMenu, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QFont
import sys
import os
import shutil

try:
    import qtawesome as qta
    HAS_ICONS = True
except ImportError:
    HAS_ICONS = False

from utils.config import config
from core.recorder import Recorder
from core.screen_capture import ScreenCapturer
from gui.area_selector import AreaSelector
from gui.countdown_overlay import CountdownOverlay
from utils.audio_devices import AudioDeviceManager
from utils.hotkeys import HotkeyManager

# ダークテーマのスタイルシート
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;
    font-size: 10pt;
}
QGroupBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: #89b4fa;
}
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #585b70;
}
QPushButton:pressed {
    background-color: #6c7086;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
}
QPushButton#recordBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-weight: bold;
    font-size: 12pt;
}
QPushButton#recordBtn:hover {
    background-color: #eba0ac;
}
QPushButton#recordBtn[recording="true"] {
    background-color: #a6e3a1;
}
QPushButton#pauseBtn {
    background-color: #fab387;
    color: #1e1e2e;
}
QPushButton#pauseBtn:hover {
    background-color: #f9e2af;
}
QComboBox {
    background-color: #45475a;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 100px;
}
QComboBox:hover {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    selection-background-color: #585b70;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #585b70;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QCheckBox::indicator:hover {
    border-color: #89b4fa;
}
QLabel {
    background-color: transparent;
}
QStatusBar {
    background-color: #181825;
    border-top: 1px solid #313244;
}
QStatusBar QLabel {
    color: #a6adc8;
}
QFrame#separator {
    background-color: #45475a;
    max-height: 1px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("画面録画ツール (Screen Recorder)")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)
        
        # スタイルシート適用
        self.setStyleSheet(DARK_STYLESHEET)
        
        # 依存関係チェック
        self._check_dependencies()
        
        # ホットキーマネージャー
        self.hotkey_manager = HotkeyManager()
        self.hotkey_manager.toggle_recording_triggered.connect(self._toggle_recording)
        self.hotkey_manager.toggle_pause_triggered.connect(self._toggle_pause)
        self.hotkey_manager.start_listening()
        
        # レコーダーの初期化
        self.recorder = Recorder()
        self.recorder.time_updated.connect(self._update_timer)
        self.recorder.status_changed.connect(self._update_status)
        self.recorder.finished.connect(self._on_recording_finished)
        self.recorder.error_occurred.connect(self._on_error)
        
        # コンポーネントの初期化
        self.area_selector = AreaSelector()
        self.area_selector.selection_completed.connect(self._on_area_selected)
        
        self.countdown_overlay = CountdownOverlay()
        self.countdown_overlay.finished.connect(self._start_recording_internal)

        self.selected_area = None

        # メインウィジェットとレイアウトの設定
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # 各セクションの初期化
        self._init_recording_mode_section(main_layout)
        self._init_audio_section(main_layout)
        self._init_quality_section(main_layout)
        self._init_output_section(main_layout)
        self._init_controls_section(main_layout)
        self._init_status_bar()
        self._init_system_tray()

    def _get_icon(self, name, color='#cdd6f4'):
        """QtAwesomeアイコンを取得。ライブラリがない場合はNone"""
        if HAS_ICONS:
            return qta.icon(name, color=color)
        return None

    def _check_dependencies(self):
        if not shutil.which("ffmpeg"):
            QMessageBox.warning(self, "警告", 
                "FFmpegが見つかりませんでした。\n"
                "録画機能が正しく動作しない可能性があります。\n"
                "FFmpegをインストールしてPATHに通してください。")

    def _init_recording_mode_section(self, parent_layout):
        group = QGroupBox("  録画モード")
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # モードラベル with icon
        mode_label = QLabel("モード:")
        icon = self._get_icon('fa5s.desktop', '#89b4fa')
        if icon:
            mode_label.setPixmap(icon.pixmap(16, 16))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["全画面録画", "範囲指定録画"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        
        # モニタ選択用コンボボックス
        self.screen_combo = QComboBox()
        monitors = ScreenCapturer.get_monitors()
        for i, m in monitors:
            width = m["width"]
            height = m["height"]
            self.screen_combo.addItem(f"モニタ {i} ({width}x{height})", i)
            
        self.cursor_check = QCheckBox("マウスカーソルを表示")
        self.cursor_check.setChecked(config.show_cursor)
        self.cursor_check.toggled.connect(lambda c: setattr(config, 'show_cursor', c))
        
        layout.addWidget(mode_label)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.screen_combo)
        layout.addWidget(self.cursor_check)
        layout.addStretch()
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _init_audio_section(self, parent_layout):
        group = QGroupBox("  音声設定")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # システム音声
        sys_layout = QHBoxLayout()
        self.sys_audio_check = QCheckBox("システム音声を録音")
        self.sys_audio_check.setChecked(config.use_system_audio)
        self.sys_audio_check.toggled.connect(lambda c: setattr(config, 'use_system_audio', c))
        
        icon = self._get_icon('fa5s.volume-up', '#a6e3a1')
        if icon:
            sys_icon_label = QLabel()
            sys_icon_label.setPixmap(icon.pixmap(16, 16))
            sys_layout.addWidget(sys_icon_label)
        sys_layout.addWidget(self.sys_audio_check)
        sys_layout.addStretch()
        
        # マイク音声
        mic_layout = QHBoxLayout()
        self.mic_audio_check = QCheckBox("マイク音声を録音")
        self.mic_audio_check.setChecked(config.use_mic_audio)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setEnabled(config.use_mic_audio)
        
        # マイクデバイスの列挙
        devices = AudioDeviceManager.get_input_devices()
        for dev in devices:
            self.mic_combo.addItem(dev['name'], dev['id'])
            
        self.mic_combo.currentIndexChanged.connect(self._on_mic_changed)
        self.mic_audio_check.toggled.connect(self._on_mic_toggled)
        
        icon = self._get_icon('fa5s.microphone', '#fab387')
        if icon:
            mic_icon_label = QLabel()
            mic_icon_label.setPixmap(icon.pixmap(16, 16))
            mic_layout.addWidget(mic_icon_label)
        mic_layout.addWidget(self.mic_audio_check)
        mic_layout.addWidget(self.mic_combo)
        mic_layout.addStretch()
        
        layout.addLayout(sys_layout)
        layout.addLayout(mic_layout)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _init_quality_section(self, parent_layout):
        group = QGroupBox("  品質・その他")
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # フレームレート
        fps_label = QLabel("FPS:")
        icon = self._get_icon('fa5s.tachometer-alt', '#f9e2af')
        if icon:
            fps_label.setPixmap(icon.pixmap(16, 16))
        
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["15", "30", "60"])
        self.fps_combo.setCurrentText(str(config.fps))
        self.fps_combo.currentTextChanged.connect(self._on_fps_changed)
        
        # カウントダウン
        self.countdown_check = QCheckBox("録画開始カウントダウン")
        self.countdown_check.setChecked(config.countdown_enabled)
        self.countdown_check.toggled.connect(lambda c: setattr(config, 'countdown_enabled', c))
        
        layout.addWidget(fps_label)
        layout.addWidget(self.fps_combo)
        layout.addStretch()
        layout.addWidget(self.countdown_check)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _init_output_section(self, parent_layout):
        group = QGroupBox("  保存先")
        layout = QHBoxLayout()
        layout.setSpacing(8)
        
        icon = self._get_icon('fa5s.folder-open', '#89dceb')
        if icon:
            folder_icon_label = QLabel()
            folder_icon_label.setPixmap(icon.pixmap(16, 16))
            layout.addWidget(folder_icon_label)
        
        self.path_label = QLabel(config.output_dir)
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        
        browse_btn = QPushButton("参照...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_folder)
        icon = self._get_icon('fa5s.folder', '#89dceb')
        if icon:
            browse_btn.setIcon(icon)
        
        # GIFオプション
        self.gif_check = QCheckBox("GIFとしても保存")
        icon = self._get_icon('fa5s.image', '#cba6f7')
        if icon:
            # GIF check icon is handled via checkbox
            pass
        
        layout.addWidget(self.path_label, 1)
        layout.addWidget(browse_btn)
        layout.addWidget(self.gif_check)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _init_controls_section(self, parent_layout):
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        self.record_btn = QPushButton("  録画開始 (F9)")
        self.record_btn.setObjectName("recordBtn")
        self.record_btn.setMinimumHeight(48)
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.clicked.connect(self._toggle_recording)
        icon = self._get_icon('fa5s.circle', '#1e1e2e')
        if icon:
            self.record_btn.setIcon(icon)
        
        self.pause_btn = QPushButton("  一時停止 (F10)")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.setMinimumHeight(48)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.clicked.connect(self._toggle_pause)
        icon = self._get_icon('fa5s.pause', '#1e1e2e')
        if icon:
            self.pause_btn.setIcon(icon)
        
        layout.addWidget(self.record_btn)
        layout.addWidget(self.pause_btn)
        
        parent_layout.addLayout(layout)

    def _init_status_bar(self):
        self.status_label = QLabel("待機中")
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 11pt;")
        
        status_prefix = QLabel("● ステータス:")
        status_prefix.setStyleSheet("color: #a6e3a1;")
        
        self.statusBar().addWidget(status_prefix)
        self.statusBar().addWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.time_label)

    def _init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self._get_icon('fa5s.video', '#f38ba8')
        if icon:
            self.tray_icon.setIcon(icon)
        else:
            from PyQt6.QtGui import QPixmap, QColor
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor("#f38ba8"))
            self.tray_icon.setIcon(QIcon(pixmap))
        
        menu = QMenu()
        show_action = QAction("表示", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(self.close)
        
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "保存先フォルダを選択", config.output_dir)
        if folder:
            config.output_dir = folder
            self.path_label.setText(folder)

    def _on_mic_toggled(self, checked):
        config.use_mic_audio = checked
        self.mic_combo.setEnabled(checked)

    def _on_mic_changed(self, index):
        data = self.mic_combo.currentData()
        config.mic_device_id = data

    def _on_fps_changed(self, text):
        config.fps = int(text)

    def _on_mode_changed(self, index):
        # 0: 全画面, 1: 範囲指定
        # 全画面のときだけモニタ選択を表示
        self.screen_combo.setVisible(index == 0)

    def _toggle_recording(self):
        if self.recorder.is_recording:
            # 停止処理
            self.recorder.stop_recording()
            self.record_btn.setText("  録画開始 (F9)")
            icon = self._get_icon('fa5s.circle', '#1e1e2e')
            if icon:
                self.record_btn.setIcon(icon)
            self.record_btn.setProperty("recording", False)
            self.record_btn.style().unpolish(self.record_btn)
            self.record_btn.style().polish(self.record_btn)
            self.pause_btn.setEnabled(False)
            self._update_ui_state(True)
        else:
            # 開始処理
            self._prepare_recording()

    def _prepare_recording(self):
        mode_index = self.mode_combo.currentIndex()
        if mode_index == 1: # 範囲指定
            self.hide() # メインウィンドウを隠す
            self.area_selector.show()
        else:
            self._start_sequence()

    def _on_area_selected(self, rect):
        self.selected_area = rect
        self.show()
        self._start_sequence()

    def _start_sequence(self):
        if config.countdown_enabled:
            self.hide()
            self.countdown_overlay.start()
        else:
            self._start_recording_internal()

    def _start_recording_internal(self):
        # ウィンドウを最小化
        self.showMinimized()
        
        if self.mode_combo.currentIndex() == 0:
            area = None
        else:
            area = self.selected_area

        monitor_idx = self.screen_combo.currentData()
        output_format = 'gif' if self.gif_check.isChecked() else 'mp4'
        self.recorder.start_recording(region=area, monitor_index=monitor_idx, output_format=output_format)
        
        self.record_btn.setText("  録画停止 (F9)")
        icon = self._get_icon('fa5s.stop', '#1e1e2e')
        if icon:
            self.record_btn.setIcon(icon)
        self.record_btn.setProperty("recording", True)
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("  一時停止 (F10)")
        self._update_ui_state(False)

    def _toggle_pause(self):
        if self.recorder.is_paused:
            self.recorder.resume_recording()
            self.pause_btn.setText("  一時停止 (F10)")
            icon = self._get_icon('fa5s.pause', '#1e1e2e')
            if icon:
                self.pause_btn.setIcon(icon)
        else:
            self.recorder.pause_recording()
            self.pause_btn.setText("  再開 (F10)")
            icon = self._get_icon('fa5s.play', '#1e1e2e')
            if icon:
                self.pause_btn.setIcon(icon)

    def _update_ui_state(self, enabled):
        self.mode_combo.setEnabled(enabled)
        self.screen_combo.setEnabled(enabled)
        self.gif_check.setEnabled(enabled)
        self.fps_combo.setEnabled(enabled)
        self.sys_audio_check.setEnabled(enabled)
        self.mic_audio_check.setEnabled(enabled)
        self.mic_combo.setEnabled(enabled and config.use_mic_audio)

    def _update_timer(self, time_str):
        self.time_label.setText(time_str)

    def _update_status(self, status):
        self.status_label.setText(status)

    def _on_recording_finished(self, filepath):
        self.status_label.setText("待機中")
        self.time_label.setText("00:00:00")
        self.showNormal() # ウィンドウを復帰
        QMessageBox.information(self, "録画完了", f"動画を保存しました:\n{filepath}")

    def _on_error(self, message):
        self.showNormal()
        QMessageBox.critical(self, "エラー", f"録画中にエラーが発生しました:\n{message}")
        # リセット処理
        self.record_btn.setText("  録画開始 (F9)")
        icon = self._get_icon('fa5s.circle', '#1e1e2e')
        if icon:
            self.record_btn.setIcon(icon)
        self.pause_btn.setEnabled(False)
        self._update_ui_state(True)

    def closeEvent(self, event):
        if self.recorder.is_recording:
            reply = QMessageBox.question(self, "確認", "録画中です。終了しますか？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            else:
                self.recorder.stop_recording()
        
        # ホットキーのクリーンアップ
        self.hotkey_manager.stop_listening()
        super().closeEvent(event)


