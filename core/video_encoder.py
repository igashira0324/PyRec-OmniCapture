import ffmpeg
import numpy as np
import threading
import subprocess

class VideoEncoder:
    def __init__(self, output_path, resolution, fps=30):
        self.output_path = output_path
        self.width, self.height = resolution
        self.fps = fps
        self.process = None
        
    def start(self):
        """FFmpegプロセスを開始"""
        # 入力: rawvideo (pipeから)
        # 出力: h264/aac mp4
        
        # 映像入力の設定
        input_video = ffmpeg.input('pipe:', format='rawvideo', pix_fmt='bgra', s='{}x{}'.format(self.width, self.height), r=self.fps)
        
        # 音声入力の設定 (別途pipeが必要だが、簡単のためまずは映像のみ、またはmuxが必要)
        # 今回は映像ストリームをメインに実装し、音声はffmpeg-pythonの複雑な構成が必要になるため
        # 別のスレッドで音声ファイルを保存して後で結合するか、
        # リアルタイムで複数のパイプを扱う高度な実装が必要。
        # ここではシンプルに映像のみのエンコードフローを記述し、後で拡張する
        
        self.process = (
            input_video
            .output(self.output_path, vcodec='libx264', pix_fmt='yuv420p', preset='ultrafast')
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )
        
    def write_frame(self, frame):
        """フレームデータを書き込む"""
        if self.process:
            try:
                self.process.stdin.write(frame.tobytes())
            except Exception as e:
                print(f"Error writing frame: {e}")

    def stop(self):
        """プロセスを終了"""
        if self.process:
            self.process.stdin.close()
            self.process.wait()
            self.process = None
