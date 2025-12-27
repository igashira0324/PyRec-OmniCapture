from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

class CountdownOverlay(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        layout = QVBoxLayout()
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # フォント設定
        font = QFont("Arial", 200, QFont.Weight.Bold)
        self.label.setFont(font)
        
        # 色設定 (白文字、黒縁取りなどはスタイルシートで)
        self.label.setStyleSheet("color: white; font-weight: bold;")
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_count)
        self.count = 3
        
    def start(self):
        self.count = 3
        self.label.setText(str(self.count))
        self.show()
        self.timer.start(1000)
        
    def _update_count(self):
        self.count -= 1
        if self.count > 0:
            self.label.setText(str(self.count))
        else:
            self.timer.stop()
            self.close()
            self.finished.emit()

    def paintEvent(self, event):
        # 背景を少し暗くする
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
