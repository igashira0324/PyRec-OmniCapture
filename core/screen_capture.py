import time
import os
import mss
import numpy as np
from PIL import Image, ImageDraw
from utils.config import config

class ScreenCapturer:
    def __init__(self):
        # メインスレッドでモニタ情報を取得
        with mss.mss() as sct:
            self.monitor = sct.monitors[1] # デフォルトはプライマリモニタ
            
        self.running = False
        self.paused = False
        self.first_frame_debug = True
        
    @staticmethod
    def get_monitors():
        """利用可能なモニタのリストを返す"""
        with mss.mss() as sct:
            # monitors[0] は全画面結合、1以降が各モニタ
            # インデックスと情報を返す
            return [(i, m) for i, m in enumerate(sct.monitors) if i > 0]
        
    def start_capture(self, region=None, monitor_index=1, show_cursor=True, target_fps=30):
        """
        キャプチャを開始するジェネレータ
        region: (top, left, width, height) のタプル。指定された場合はmonitor_indexより優先
        monitor_index: 全画面録画時の対象モニタインデックス (MSS準拠、1始まり)
        """
        self.running = True
        self.paused = False
        
        frame_interval = 1.0 / target_fps
        last_frame_time = time.time()
        
        # スレッド内で新しいインスタンスを作成（必須）
        with mss.mss() as sct:
            # DEBUG: モニタ情報を出力
            for i, m in enumerate(sct.monitors):
                print(f"[DEBUG] MSS Monitor {i}: {m}")

            # 録画範囲の設定
            if region:
                monitor = {
                    "top": int(region[1]), 
                    "left": int(region[0]), 
                    "width": int(region[2]), 
                    "height": int(region[3])
                }
                print(f"[DEBUG] Capture Config: Region={monitor}")
                print(f"[DEBUG] Capture Config: Region={monitor}")
            else:
                # 指定されたモニタを使用
                if monitor_index < len(sct.monitors):
                    monitor = sct.monitors[monitor_index]
                else:
                    monitor = sct.monitors[1] # フォールバック
                print(f"[DEBUG] Capture Config: Full Screen (Monitor {monitor_index})={monitor}")
            
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue
                    
                start_time = time.time()
                
                # スクリーンショット取得
                try:
                    sct_img = sct.grab(monitor)
                    frame = np.array(sct_img)
                    
                    # DEBUG: 最初のフレームを保存して確認
                    if self.first_frame_debug:
                        self.first_frame_debug = False
                        try:
                            from PIL import Image
                            debug_img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                            debug_img.save(os.path.join(config.output_dir, "debug_frame.png"))
                            print(f"[DEBUG] Saved debug_frame.png. Region: {monitor}")
                        except Exception as e:
                            print(f"[DEBUG] Failed to save debug frame: {e}")

                    yield frame, start_time
                except Exception as e:
                    print(f"Capture error: {e}")
                    break
                
                # FPS制御
                processing_time = time.time() - start_time
                sleep_time = max(0, frame_interval - processing_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
        
    def _draw_cursor(self, frame):
        # 将来的な実装のためにプレースホルダー
        return frame
