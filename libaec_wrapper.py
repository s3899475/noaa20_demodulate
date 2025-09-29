import platform
from ctypes import *

import numpy as np

if platform.system() == "Linux":
    libaec = CDLL("libaec.so")
elif platform.system() == "Windows":
    libaec = cdll.libaec

AEC_DATA_MSB = 4
AEC_DATA_PREPROCESS = 8
AEC_FLUSH = 1

class AEC_Stream(Structure):
    _fields_ = [
        ("next_in", POINTER(c_ubyte)),
        ("avail_in", c_size_t),
        ("total_in", c_size_t),
        #("next_out", POINTER(c_ubyte)),
        ("next_out", POINTER(c_uint16)),
        ("avail_out", c_size_t),
        ("total_out", c_size_t),
        ("bits_per_sample", c_uint),
        ("block_size", c_uint),
        ("rsi", c_uint),
        ("flags", c_uint),
        ("internal_state", c_void_p)
    ]


# decode aec compressed data using libaec
aec_cfg = AEC_Stream()
aec_cfg.bits_per_sample = 15
aec_cfg.block_size = 8
aec_cfg.rsi = 128
aec_cfg.flags = AEC_DATA_MSB | AEC_DATA_PREPROCESS


# out_data == array of uint16
def aec_decode(in_data, out_data):
    aec_cfg.next_in =  in_data.ctypes.data_as(POINTER(c_ubyte))
    #aec_cfg.avail_in = data_payload_size - 1;
    aec_cfg.avail_in = len(in_data) - 1
    aec_cfg.next_out = out_data.ctypes.data_as(POINTER(c_uint16))
    #aec_cfg.avail_out = current_segment.detector_data[detector][det_n].size() * 2;
    aec_cfg.avail_out = len(out_data) * 2

    libaec.aec_decode_init(pointer(aec_cfg))
    libaec.aec_decode(pointer(aec_cfg), AEC_FLUSH);
    libaec.aec_decode_end(pointer(aec_cfg));


if __name__ == "__main__":
    in_data = np.array([0, 1, 2, 3], dtype=np.uint8)
    out_data = np.array([0]*32, dtype=np.uint8)

    for i in range(10000):
        aec_decode(in_data, out_data)
    print(in_data)
    print(out_data)
