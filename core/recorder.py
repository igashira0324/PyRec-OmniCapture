import threading
import time
import os
import wave
import numpy as np
import ffmpeg
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from core.screen_capture import ScreenCapturer
from core.audio_capture import AudioCapturer
from core.video_encoder import VideoEncoder
from utils.config import config

class Recorder(QObject):
    # シグナル定義
    time_updated = pyqtSignal(str) # 経過時間 (HH:MM:SS)
    status_changed = pyqtSignal(str) # ステータス文字列
    finished = pyqtSignal(str) # 保存完了時のパス
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.screen_capturer = ScreenCapturer()
        self.audio_capturer = AudioCapturer()
        self.video_encoder = None
        
        self.is_recording = False
        self.is_paused = False
        self.start_time = 0
        self.elapsed_time = 0
        self.pause_start_time = 0
        
        self.recording_thread = None
        
        # 一時ファイルパス
        self.temp_video_path = ""
        self.temp_audio_path = ""
        self.final_output_path = ""
        self.wave_file = None

    def start_recording(self, region=None, monitor_index=1, output_format='mp4'):
        if self.is_recording:
            return

        if not os.path.exists(config.output_dir):
            os.makedirs(config.output_dir)
            
        self.output_format = output_format

        # パス設定
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.mp4" # 中間ファイルは常にMP4
        self.final_output_path = os.path.join(config.output_dir, filename)
        
        self.temp_video_path = os.path.join(config.output_dir, "temp_video.mp4")
        self.temp_audio_path = os.path.join(config.output_dir, "temp_audio.wav")
        
        # 解像度の決定 (region or monitor size)
        if region:
            width, height = region[2], region[3]
        else:
            # 指定モニタの解像度を取得するために一時的にmssを使用
            import mss
            with mss.mss() as sct:
                if monitor_index < len(sct.monitors):
                    monitor = sct.monitors[monitor_index]
                else:
                    monitor = sct.monitors[1]
                width, height = monitor["width"], monitor["height"]

        # 幅・高さは偶数である必要があるので調整
        width = width if width % 2 == 0 else width - 1
        height = height if height % 2 == 0 else height - 1
        
        # 範囲指定の場合、調整した幅・高さでregionを更新してキャプチャに渡す必要がある
        final_region = None
        if region:
            final_region = (region[0], region[1], width, height)
        
        # 動画エンコーダ開始
        self.video_encoder = VideoEncoder(self.temp_video_path, (width, height), fps=config.fps)
        self.video_encoder.start()
        
        # 音声ファイル準備
        self._prepare_audio_file()

        # スレッド開始
        self.is_recording = True
        self.is_paused = False
        self.start_time = time.time()
        self.elapsed_time = 0
        
        self.audio_capturer.start_capture(
            use_system=config.use_system_audio,
            use_mic=config.use_mic_audio,
            mic_device_id=config.mic_device_id
        )

        self.recording_thread = threading.Thread(target=self._recording_loop, args=(final_region, monitor_index))
        self.recording_thread.start()
        
        self.status_changed.emit("録画中")

    def _prepare_audio_file(self):
        try:
            self.wave_file = wave.open(self.temp_audio_path, 'wb')
            self.wave_file.setnchannels(2) # AudioCapturer固定値
            self.wave_file.setsampwidth(2) # 16bit = 2bytes
            self.wave_file.setframerate(44100) # AudioCapturer固定値
        except Exception as e:
            print(f"Error creating wave file: {e}")

    def _recording_loop(self, region, monitor_index):
        capture_gen = self.screen_capturer.start_capture(region=region, monitor_index=monitor_index, show_cursor=config.show_cursor, target_fps=config.fps)
        
        try:
            for frame, timestamp in capture_gen:
                if not self.is_recording:
                    break
                
                # 一時停止中は書き込みスキップ
                if self.is_paused:
                    continue
                
                # 映像書き込み
                self.video_encoder.write_frame(frame)
                
                # 音声書き込み
                # キューに溜まっている分をすべて書き出す
                while True:
                    audio_data = self.audio_capturer.get_audio_data()
                    if audio_data is None:
                        break
                    if self.wave_file:
                        # float32 (-1.0 to 1.0) -> int16
                        audio_int16 = (audio_data * 32767).astype(np.int16)
                        self.wave_file.writeframes(audio_int16.tobytes())
                
                # 時間更新
                self._update_time_label()

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._cleanup_capture()
            self._finalize_output()

    def _update_time_label(self):
        now = time.time()
        # TODO: より正確な累積時間計算
        total_sec = int(now - self.start_time)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        seconds = total_sec % 60
        self.time_updated.emit(f"{hours:02}:{minutes:02}:{seconds:02}")

    def pause_recording(self):
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self.screen_capturer.pause()
            self.audio_capturer.pause()
            self.pause_start_time = time.time()
            self.status_changed.emit("一時停止中")

    def resume_recording(self):
        if self.is_recording and self.is_paused:
            self.is_paused = False
            pause_duration = time.time() - self.pause_start_time
            self.start_time += pause_duration
            
            self.screen_capturer.resume()
            self.audio_capturer.resume()
            self.status_changed.emit("録画中")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            # スレッド終了を待つ
            # _cleanup_capture と _finalize_output はスレッド内で呼ばれる

    def _cleanup_capture(self):
        self.screen_capturer.stop()
        self.audio_capturer.stop()
        if self.video_encoder:
            self.video_encoder.stop()
        if self.wave_file:
            self.wave_file.close()

    def _finalize_output(self):
        self.status_changed.emit("エンコード中...")
        
        # 映像と音声を結合
        try:
            if not os.path.exists(self.temp_video_path):
                raise Exception("Video file not generated")
                
            input_video = ffmpeg.input(self.temp_video_path)
            
            if os.path.exists(self.temp_audio_path) and os.path.getsize(self.temp_audio_path) > 100:
                input_audio = ffmpeg.input(self.temp_audio_path)
                stream = ffmpeg.output(input_video, input_audio, self.final_output_path, vcodec='copy', acodec='aac')
            else:
                # 音声がない場合
                stream = ffmpeg.output(input_video, self.final_output_path, vcodec='copy')
            
            stream.run(overwrite_output=True, quiet=True)
            
            # GIF変換が必要な場合
            if hasattr(self, 'output_format') and self.output_format == 'gif':
                self.status_changed.emit("GIF変換中...")
                mp4_path = self.final_output_path
                gif_path = mp4_path.replace(".mp4", ".gif")
                
                try:
                    # FPS制限とパレット生成で高品質化
                    # ffmpeg -i input.mp4 -vf "fps=15,scale=...:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output.gif
                    # シンプルに実行
                    (
                        ffmpeg
                        .input(mp4_path)
                        .filter('fps', fps=15) # GIFは容量削減のためFPS下げる
                        .output(gif_path)
                        .run(overwrite_output=True, quiet=True)
                    )
                    
                    # 生成成功したらMP4は削除？ 今回は両方残すか、GIFのみにするか。通常は置換
                    if os.path.exists(gif_path):
                        os.remove(mp4_path)
                        self.finished.emit(gif_path)
                    else:
                        self.finished.emit(mp4_path)
                        
                except Exception as e:
                    print(f"GIF Conversion failed: {e}")
                    self.finished.emit(mp4_path) # 失敗したらMP4を返す
            else:
                self.finished.emit(self.final_output_path)
            
        except Exception as e:
            self.error_occurred.emit(f"Finalize Error: {e}")
        finally:
            # 一時ファイル削除
            try:
                if os.path.exists(self.temp_video_path):
                    os.remove(self.temp_video_path)
                if os.path.exists(self.temp_audio_path):
                    os.remove(self.temp_audio_path)
            except Exception:
                pass

