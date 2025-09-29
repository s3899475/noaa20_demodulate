import io
import os
import mmap

import numpy as np
import matplotlib.pyplot as plt
from construct import *

import aec_wrapper


frame_len = 892
#n_frames = 500
#n_frames = 5000
#n_frames = 50000
n_frames = 500000
VIIRS_VCID = 16
#MPDU_SIZE = 884 # FEC not used !!!
MPDU_SIZE = 886

AOS_HDR_NOT_PRESENT = 0b111_1111_1111
AOS_ONLY_IDLE_DATA  = 0b111_1111_1110

# https://ccsds.org/Pubs/732x0b3e1s.pdf

# ccsds aos space packet
VCDU = BitStruct(
    'transfer_frame_version_number' / BitsInteger(2),
    'spacecraft_id' / Bytewise(Byte),
    'virtual_channel_id' / BitsInteger(6),
    'virtual_channel_frame_count' / Bytewise(Bytes(3)),
    'replay_flag' / Flag,
    'vc_frame_count_usage_flag' / Flag, # unused
    'reserved_spare' / BitsInteger(2), # unused
    'vc_frame_count_cycle' / BitsInteger(4), # unused
    #'frame_header_error_control' / Bytewise(Bytes(2)), # not present!!
    'payload' / Bytewise(Bytes(MPDU_SIZE))
)

M_PDU = BitStruct(
    'reserved_spare' / BitsInteger(5), # should be set to all zeros, but it's not???
    'first_header_pointer' / BitsInteger(11),
    'packet_zone' / Bytewise(Bytes(MPDU_SIZE-2))
)

# https://ccsds.org/Pubs/133x0b2e2.pdf
PRIMARY_HDR = BitStruct(
    'packet_version_number' / BitsInteger(3),
    'packet_type' / Flag,
    'secondary_header_flag' / Flag, # 1 if packet has a secondary header
    'application_process_identifier' / BitsInteger(11),
    'sequence_flags' / BitsInteger(2), # 1 if first packet, 2 if last packet
    'sequence_count' / BitsInteger(14),
    'packet_length' / Bytewise(Int16ub)
)


CCSDS_TIME = Struct(
    'day' / Int16ub, # days since January 1st 1958
    'millisecond' / Int32ub, # milliseconds since start of day
    'microseconds' / Int16ub
)


# https://github.com/luigifcruz/weatherdump/blob/master/src/protocols/hrd/processor/parser/segment/header.go
# https://www.star.nesdis.noaa.gov/jpss/documents/CDFCB/GSFC_474-00001-07-01_CDFCB_External_Vol.7-1_JPSS_Downlink_Data_Formats__D34862-07-01_.pdf
SECONDARY_HDR = Struct(
    'time' / CCSDS_TIME,
    'number_of_segments' / Byte, # number of packets in sequence minus 1
    'spare' / Byte # unused
)

# for start packets (seqid = 1)
HR_METADATA = Struct (
    'pkt_id' / BitStruct(
        'ham_side' / Flag,
        'scan_sync' / Flag,
        'test_data_pattern' / BitsInteger(4),
        'reserved' / BitsInteger(10),
    ),
    'scan_number' / Int32ub,
    'scan_terminus' / CCSDS_TIME,
    'sensor_mode' / Byte,
    'viirs_model' / Byte,
    'fsw_version' / Int16ub,
    'band_control_word' / Int32ub,
    'partial_start' / Int16ub,
    'number_of_samples' / Int16ub,
    'sample_delay' / Int16ub,
    'reserved' / Bytes(118),
)


DETECTOR = Struct(
    #'fill_data' / Bytes(2),
    'fill_size' / Byte,
    'fill_data2' / Byte,
    'checksum_offset' / Int16ub,
    'data' / Bytes(this.checksum_offset-4),
    'checksum' / Bytes(4),
    'syncword' / Bytes(4)
)


# for middle packets (seqid = 0)
HR_DETECTOR_DATA = Struct(
    'start' / BitStruct(
        'inegrity_check' / BitsInteger(1), # 0 for no error
        'test_data_pattern' / BitsInteger(4),
        'reserved' / BitsInteger(11)
    ),
    'band' / Byte,
    'detector' / Byte,
    'sync_word_pattern' / Bytes(4),
    #'reserved' / Bytes(64),
    'reserved' / Bytes(64),
    'detector_data' / Array(6, DETECTOR)
    #'data' / GreedyBytes
    #'data' / OffsettedEnd(-2, GreedyBytes), # make room for checksum
)

VIIRS_USER_DATA = Struct(
    'sequence_count' / Int32ub,
    'packet_time' / CCSDS_TIME,
    'format_version' / Byte,
    'instrument_number' / Byte,
    'spare' / Bytes(2),
    'hr_metadata' / HR_METADATA,
    'checksum' / Bytes(2)
)



VIIRS_USER_DATA_MIDDLE = Struct(
    'sequence_count' / Bytes(4),
    'packet_time' / CCSDS_TIME,
    'format_version' / Byte,
    'instrument_number' / Byte,
    'spare' / Bytes(2),
    'hr_detector_data' / HR_DETECTOR_DATA,
    #'checksum' / Bytes(2) # not present?
)


#uint16_t first_header_pointer = (cadu[10] & 0b111) << 8 | cadu[11];

print(f"Reading {n_frames} CADUs ({frame_len*n_frames/1_000_000} MB) and viltering for VIIRS data")

"""
viirs_data = []
with open("Code/a.out", "rb") as f:
    with mmap.mmap(f.fileno(), frame_len*n_frames, access=mmap.ACCESS_READ) as mm:
        for i in range(n_frames):
            
            #vcdu_data = VCDU.parse_stream(mm)
            data = mm.read(frame_len)
            vcdu_data = VCDU.parse(data)

            if vcdu_data.virtual_channel_id == VIIRS_VCID:
                chunk = M_PDU.parse(vcdu_data.payload)
                viirs_data.append(chunk)
"""
viirs_data = []
with open("Code/a.out", "rb") as f:
    file_data = f.read(frame_len*n_frames)

print("Parsing CADUs")
for i in range(0, frame_len*n_frames, frame_len):
    frame = file_data[i:i+frame_len]
    vcid = frame[1] & 0b00111111
    #vcdu_data = VCDU.parse(file_data[i:i+frame_len])
    #vcid = vcdu_data.virtual_channel_id
    
    if vcid == VIIRS_VCID:
        #viirs_data.append(M_PDU.parse(vcdu_data.payload))
        viirs_data.append(M_PDU.parse(frame[6:]))
    

# demux
print("Demuxing CADUs")
packets = []

# padu packet zone buffer
arr = bytearray()

at_header=True
cur_hdr = None
bytes_ready = 0
data_needed = 0

for pdu in viirs_data:
    ptr = pdu.first_header_pointer
    if ptr == AOS_ONLY_IDLE_DATA:
        continue
    
    if cur_hdr == None: # get first header
        if ptr < MPDU_SIZE - PRIMARY_HDR.sizeof():
            cur_hdr = PRIMARY_HDR.parse(pdu.packet_zone[ptr:ptr+PRIMARY_HDR.sizeof()])
            data_needed = cur_hdr.packet_length

            arr += pdu.packet_zone[ptr+PRIMARY_HDR.sizeof():]
            at_header = False

    else: # read more bytes
        arr += pdu.packet_zone

        while len(arr) >= data_needed:
            if at_header:
                cur_hdr = PRIMARY_HDR.parse(arr[:PRIMARY_HDR.sizeof()])
                arr = arr[PRIMARY_HDR.sizeof():]

                if cur_hdr.packet_version_number != 0:
                    raise ValueError("Wrong packet version number")

                data_needed = cur_hdr.packet_length
                at_header = False
                
            else:
                packets.append((cur_hdr, arr[:data_needed+1]))
                arr = arr[data_needed+1:]
                
                data_needed = PRIMARY_HDR.sizeof()
                at_header = True


# extract detector data
print("Extracting detector data")
VIIRS_M6_APID = 805
VIIRS_M6_ZONEWIDTHS = [640, 368, 592, 592, 368, 640]
VIIRS_M6_ZONEHEIGHT = 16
VIIRS_M6_BITS = 16
#  flag values
SEQUENCE_MIDDLE = 0
SEQUENCE_START = 1
SEQUENCE_END = 2

def bit_slicer_detector(length, fillsize):
    bits = 0
    by = 0

    while fillsize % 8 != 0:
        bits += 1
        fillsize -= 1

    by = length - (fillsize // 8)

    if by > length or by < 0:
        return length
    else:
        return by + 1
    

segments = []

seg = [[np.empty(0)] * 6 for _ in range(16)]
for prim_hdr, data in packets:
    # filter for apid of VIIRS M6
    if prim_hdr.application_process_identifier == VIIRS_M6_APID-1:

        #print(prim_hdr.sequence_count)
        #print(prim_hdr.sequence_flags)
        if prim_hdr.sequence_flags == SEQUENCE_START:
            sec_hdr = SECONDARY_HDR.parse(data)
            user_data_start = VIIRS_USER_DATA.parse(data[SECONDARY_HDR.sizeof():])
            segments.append([])
            #print(prim_hdr)
            #print(sec_hdr)
            #print(user_data_start)
        elif prim_hdr.sequence_flags == SEQUENCE_MIDDLE or prim_hdr.sequence_flags == SEQUENCE_END:
            user_data = VIIRS_USER_DATA_MIDDLE.parse(data)

            detector_number = user_data.hr_detector_data.detector
            #print("Detector:", detector_number)

            for det_i, det in enumerate(user_data.hr_detector_data.detector_data):
                size = det.checksum_offset - 4
                # slice end padding off
                size = bit_slicer_detector(size, det.fill_size)
                det.data = det.data[:size]
                #print(size)

                # check if detector is empty
                if size > 8:
                    #print(det)
                    # decompress
                    # TODO: may not be correct, out data has zeros at end
                    in_data = np.frombuffer(det.data, dtype=np.uint8)
                    #print("Size")
                    #print(len(in_data))
                    #print(size)
                    out_data = np.empty(VIIRS_M6_ZONEWIDTHS[det_i]*VIIRS_M6_ZONEHEIGHT, dtype=np.uint16)
                    aec_wrapper.aec_decode(
                        in_data,
                        out_data
                    )

                    # convert to little endian
                    for i in range(len(out_data)):
                        n = out_data[i]
                        out_data[i] = ((out_data[i] & 0xFF) << 8) | ((out_data[i] & 0xFF00) << 8)
                
                    # decimate if required
                    # decimation not required on VIIRS M6
                    
                    seg[detector_number][det_i] = out_data

        if prim_hdr.sequence_flags == SEQUENCE_END:
            segments.append(seg)
            seg = [[np.empty(0)] * 6 for _ in range(16)]



# create image
img = np.empty(3200*VIIRS_M6_ZONEHEIGHT*(len(segments)+1) )
print(img.size)
for seg_n, seg in enumerate(segments):
    if len(seg) == VIIRS_M6_ZONEHEIGHT:
        for seg_line in range(VIIRS_M6_ZONEHEIGHT):
            current_line = seg_n * VIIRS_M6_ZONEHEIGHT + ((VIIRS_M6_ZONEHEIGHT-1) - seg_line)
            det_offset = 0

            for det_n in range(6):
                for i in range(VIIRS_M6_ZONEWIDTHS[det_n]):
                    # TODO: what to do when det is nothing?
                    if len(seg[seg_line][det_n]) > 0:
                        img[current_line * 3200 + det_offset + i] = seg[seg_line][det_n][i] * 16

                det_offset += VIIRS_M6_ZONEWIDTHS[det_n]


img = img.reshape(3200,VIIRS_M6_ZONEHEIGHT*(len(segments)+1))
plt.imshow(img, cmap="binary")
plt.show()
