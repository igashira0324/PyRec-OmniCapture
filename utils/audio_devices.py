import soundcard as sc

class AudioDeviceManager:
    @staticmethod
    def get_input_devices():
        """利用可能な入力デバイス（マイク）のリストを返す"""
        devices = []
        try:
            # include_loopback=False で通常のマイクのみ取得
            mic_list = sc.all_microphones(include_loopback=False)
            for mic in mic_list:
                devices.append({
                    'id': mic.id, # soundcardのデバイスID (String)
                    'name': mic.name,
                    'api': 'WASAPI' # soundcard on Windows uses WASAPI
                })
        except Exception as e:
            print(f"Error querying audio devices: {e}")
        return devices

    @staticmethod
    def get_default_input_device():
        """デフォルトの入力デバイスIDを返す"""
        try:
            return sc.default_microphone().id
        except Exception:
            return None
