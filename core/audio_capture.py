import soundcard as sc
import numpy as np
import threading
import queue
import time

class AudioCapturer:
    def __init__(self):
        self.running = False
        self.paused = False
        self.audio_queue = queue.Queue()
        self.samplerate = 44100
        self.channels = 2
        self.thread = None
        
    def start_capture(self, use_system=True, use_mic=False, mic_device_id=None):
        """
        音声キャプチャ開始
        use_system: システム音声を録音するか
        use_mic: マイク音声を録音するか
        mic_device_id: マイクデバイスID (soundcard ID string)
        """
        self.running = True
        self.paused = False
        
        self.thread = threading.Thread(target=self._capture_loop, args=(use_system, use_mic, mic_device_id))
        self.thread.start()

    def _capture_loop(self, use_system, use_mic, mic_device_id):
        
        system_mic = None
        user_mic = None
        
        try:
            # システム音声用Loopbackマイクの特定
            if use_system:
                default_speaker = sc.default_speaker()
                # スピーカーと同じ名前のLoopbackマイクを探す
                all_mics = sc.all_microphones(include_loopback=True)
                for m in all_mics:
                    if m.isloopback and m.name == default_speaker.name:
                        system_mic = m
                        break
                # 見つからなければ任意のLoopback
                if not system_mic:
                    for m in all_mics:
                        if m.isloopback:
                            system_mic = m
                            break
                            
            # マイクの特定
            if use_mic:
                if mic_device_id:
                    user_mic = sc.get_microphone(mic_device_id, include_loopback=False)
                else:
                    user_mic = sc.default_microphone()

            blocksize = 1024
            
            # Context Managers
            ctx_sys = system_mic.recorder(samplerate=self.samplerate, channels=self.channels, blocksize=blocksize) if system_mic else None
            ctx_mic = user_mic.recorder(samplerate=self.samplerate, channels=self.channels, blocksize=blocksize) if user_mic else None
            
            # コンテキストに入る
            # Note: 複数のコンテキストを動的に管理するのは少し泥臭い
            
            stream_sys = ctx_sys.__enter__() if ctx_sys else None
            stream_mic = ctx_mic.__enter__() if ctx_mic else None
            
            try:
                while self.running:
                    if self.paused:
                        time.sleep(0.1)
                        continue
                        
                    data_sys = None
                    data_mic = None
                    
                    if stream_sys:
                        data_sys = stream_sys.record(numframes=blocksize)
                        
                    if stream_mic:
                        data_mic = stream_mic.record(numframes=blocksize)
                        
                    # ミキシング
                    if data_sys is not None and data_mic is not None:
                        # 長さを合わせる（念のため）
                        min_len = min(len(data_sys), len(data_mic))
                        mixed = data_sys[:min_len] + data_mic[:min_len]
                        # クリッピング防止は？ Soundcardはfloat32なので1.0を超えてもデータとしては保たれるが、
                        # 最終的にwav書き出し時にクリップされる可能性あり。
                        # ここでは単純加算とする。
                        self.audio_queue.put(mixed)
                        
                    elif data_sys is not None:
                        self.audio_queue.put(data_sys)
                        
                    elif data_mic is not None:
                        self.audio_queue.put(data_mic)
                    
                    else:
                        # 音声なし設定の場合
                        time.sleep(0.1)

            finally:
                if ctx_sys: ctx_sys.__exit__(None, None, None)
                if ctx_mic: ctx_mic.__exit__(None, None, None)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Audio capture error: {e}")

    def get_audio_data(self):
        """キューから音声データを取得"""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
