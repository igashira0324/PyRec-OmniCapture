import keyboard
import threading
from PyQt6.QtCore import QObject, pyqtSignal

class HotkeyManager(QObject):
    # シグナル定義（GUIスレッドで処理するため）
    toggle_recording_triggered = pyqtSignal() # F9
    toggle_pause_triggered = pyqtSignal()     # F10

    def __init__(self):
        super().__init__()
        self.running = False

    def start_listening(self):
        """ホットキーの監視を開始"""
        if not self.running:
            try:
                # F9: 録画開始/停止
                keyboard.add_hotkey('F9', self._on_f9)
                # F10: 一時停止/再開
                keyboard.add_hotkey('F10', self._on_f10)
                self.running = True
            except Exception as e:
                print(f"Failed to register hotkeys: {e}")

    def stop_listening(self):
        """ホットキーの監視を停止"""
        if self.running:
            try:
                keyboard.remove_hotkey('F9')
                keyboard.remove_hotkey('F10')
            except Exception:
                pass
            self.running = False

    def _on_f9(self):
        """F9押下時のコールバック"""
        self.toggle_recording_triggered.emit()

    def _on_f10(self):
        """F10押下時のコールバック"""
        self.toggle_pause_triggered.emit()
