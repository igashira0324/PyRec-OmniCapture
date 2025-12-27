import os
from pathlib import Path

class Config:
    # デフォルト設定
    DEFAULT_FPS = 30
    DEFAULT_COUNTDOWN = True
    DEFAULT_SHOW_CURSOR = True
    
    def __init__(self):
        self.fps = self.DEFAULT_FPS
        self.countdown_enabled = self.DEFAULT_COUNTDOWN
        self.show_cursor = self.DEFAULT_SHOW_CURSOR
        self.output_dir = self._get_default_output_dir()
        self.use_system_audio = True
        self.use_mic_audio = False
        self.mic_device_id = None
        
    def _get_default_output_dir(self):
        """ユーザーのビデオフォルダをデフォルトとして取得"""
        video_dir = Path.home() / "Videos" / "ScreenRecorder"
        if not video_dir.exists():
            try:
                video_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                # 失敗した場合はカレントディレクトリを使用
                return os.getcwd()
        return str(video_dir)

# グローバル設定インスタンス
config = Config()
