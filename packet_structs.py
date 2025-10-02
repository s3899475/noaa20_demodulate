from construct import *


AOS_HDR_NOT_PRESENT = 0b111_1111_1111
AOS_ONLY_IDLE_DATA  = 0b111_1111_1110


MPDU_SIZE = 886

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

