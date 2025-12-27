import sys
import os

# Apply patches early
try:
    from core.soundcard_patch import patch_soundcard
    patch_soundcard()
except ImportError:
    pass
except Exception as e:
    print(f"Failed to apply soundcard patch: {e}")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow

def main():
    # High DPI設定 (マルチモニタ環境での座標ズレ防止)
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    # 環境変数での制御も念のため
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    
    # アプリケーション全体のスタイル設定などをここで行う
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
