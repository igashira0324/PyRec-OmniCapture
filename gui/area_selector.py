from PyQt6.QtWidgets import QWidget, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QPen, QPainter, QBrush

class AreaSelector(QWidget):
    selection_completed = pyqtSignal(tuple) # (x, y, w, h)
    selection_canceled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # マルチモニタ対応: 全仮想デスクトップをカバーするように設定
        from PyQt6.QtWidgets import QApplication
        screen_geometry = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geometry)
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.current = QPoint()
        self.is_selecting = False

        # 半透明の背景色（暗くする）
        self.overlay_color = QColor(0, 0, 0, 100)
        self.border_color = QColor(255, 0, 0, 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 全体を少し暗く塗る
        painter.fillRect(self.rect(), self.overlay_color)

        if self.is_selecting and not self.origin.isNull():
            # 選択範囲をクリア（透明に）して、そこだけ明るく見せる効果
            selected_rect = QRect(self.origin, self.current).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selected_rect, Qt.GlobalColor.transparent)
            
            # 枠線を描画
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(self.border_color, 2)
            painter.setPen(pen)
            painter.drawRect(selected_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.current = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            # self.rubberBand.show() # カスタム描画を使用するため非表示のまま
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.current = event.pos()
            # self.rubberBand.setGeometry(QRect(self.origin, self.current).normalized())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = QRect(self.origin, event.pos()).normalized()
            
            # 幅や高さが小さすぎる場合は誤操作とみなす
            if rect.width() > 10 and rect.height() > 10:
                # Local to Global変換 (マルチモニタのオフセットを考慮)
                top_left_global = self.mapToGlobal(rect.topLeft())
                
                # High DPI対応: 論理座標から物理座標へ変換
                screen = self.screen()
                dpr = screen.devicePixelRatio()
                
                # Global Logical -> Global Physical
                x = int(top_left_global.x() * dpr)
                y = int(top_left_global.y() * dpr)
                w = int(rect.width() * dpr)
                h = int(rect.height() * dpr)
                
                print(f"[DEBUG] Area Selection: Local({rect.x()}, {rect.y()}) -> Global Logical({top_left_global.x()}, {top_left_global.y()}) -> Physical({x}, {y}, {w}, {h}) DPR={dpr}")
                
                self.selection_completed.emit((x, y, w, h))
                self.close()
            else:
                self.origin = QPoint()
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selection_canceled.emit()
            self.close()
