
import sys
import numpy
import time
import warnings
import soundcard.mediafoundation as mf

def patch_soundcard():
    """
    Patches soundcard.mediafoundation._Recorder._record_chunk to use numpy.frombuffer
    instead of the deprecated numpy.fromstring.
    """
    print("[INFO] Applying runtime patch for soundcard (numpy.fromstring fix)...")
    
    # Access private modules from soundcard.mediafoundation
    _ffi = mf._ffi
    _ole32 = mf._ole32
    SoundcardRuntimeWarning = mf.SoundcardRuntimeWarning

    # Define the fixed method
    def _record_chunk(self):
        """Record one chunk of audio data, as returned by WASAPI"""

        while self._capture_available_frames() == 0:
            if self._idle_start_time is None:
                self._idle_start_time = time.perf_counter_ns()

            default_block_length, minimum_block_length = self.deviceperiod
            time.sleep(minimum_block_length/4)
            elapsed_time_ns = time.perf_counter_ns() - self._idle_start_time
            
            if elapsed_time_ns / 1_000_000_000 > default_block_length * 4:
                num_frames = int(self.samplerate * elapsed_time_ns / 1_000_000_000)
                num_channels = len(set(self.channelmap))
                self._idle_start_time += elapsed_time_ns
                return numpy.zeros([num_frames * num_channels], dtype='float32')

        self._idle_start_time = None
        data_ptr, nframes, flags = self._capture_buffer()
        if data_ptr != _ffi.NULL:
            # FIX: Use frombuffer instead of fromstring
            chunk = numpy.frombuffer(_ffi.buffer(data_ptr, nframes*4*len(set(self.channelmap))), dtype='float32')
        else:
            raise RuntimeError('Could not create capture buffer')
            
        if flags & _ole32.AUDCLNT_BUFFERFLAGS_SILENT:
            chunk[:] = 0
            
        if self._is_first_frame:
            flags &= ~_ole32.AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY
            self._is_first_frame = False
            
        if flags & _ole32.AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY:
            warnings.warn("data discontinuity in recording", SoundcardRuntimeWarning)
            
        if nframes > 0:
            self._capture_release(nframes)
            return chunk.copy() # Return copy to be safe, though fromstring returned copy? frombuffer might be view. 
                                # fromstring returns a copy. frombuffer returns a view if inputs allow?
                                # _ffi.buffer result likely keeps alive? better copy.
        else:
            return numpy.zeros([0], dtype='float32')

    # Apply the patch
    mf._Recorder._record_chunk = _record_chunk
    print("[INFO] soundcard patch applied successfully.")
