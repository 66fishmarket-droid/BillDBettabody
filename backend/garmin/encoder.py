"""encoder.py — Low-level FIT binary encoder for workout files.

Writes binary FIT records using Python's built-in struct + io.BytesIO.
Reuses CrcCalculator from crc_calculator.py and type constants from fit.py.

FIT file structure (written in order):
  1. 14-byte file header  (header_size, protocol_version, profile_version,
                           data_size placeholder, .FIT magic, header CRC)
  2. Message definition records (define schema before data records)
  3. Message data records
  4. 2-byte file CRC (CRC over header + all data bytes)
"""

import io
import struct

from .crc_calculator import CrcCalculator
from .fit import BASE_TYPE_DEFINITIONS, BASE_TYPE
from .util import FIT_EPOCH_S


class FitEncoder:
    """Incrementally builds a valid FIT file in memory.

    Usage:
        enc = FitEncoder()
        enc.define_message(local_num, global_num, field_defs)
        enc.write_message(local_num, [enc.encode_value(...), ...])
        fit_bytes = enc.get_bytes()

    Global message numbers used for workouts:
        0  → file_id
        26 → workout
        27 → workout_step
    """

    PROTOCOL_VERSION = 0x10   # FIT Protocol 1.0
    PROFILE_VERSION = 21188   # 21.188.0
    HEADER_SIZE = 14

    def __init__(self):
        self._buf = io.BytesIO()
        self._defs = {}  # local_num → [(field_id, size, base_type), ...]
        # Reserve 14 bytes for the file header; back-filled lazily in get_bytes().
        self._buf.write(b'\x00' * self.HEADER_SIZE)

    def write_file_header(self):
        """No-op — header is finalised lazily in get_bytes() once data_size is known."""
        pass

    def define_message(self, local_num: int, global_num: int, field_defs: list) -> None:
        """Write a FIT message definition record.

        Args:
            local_num:  Local message number (0–15).
            global_num: FIT global message number.
            field_defs: List of (field_id, size_bytes, base_type_byte) tuples.
                        base_type_byte values come from fit.BASE_TYPE dict.
        """
        self._defs[local_num] = field_defs
        # Definition header byte: bit 6 set = definition record; bits 3–0 = local_num
        self._buf.write(struct.pack('B', 0x40 | (local_num & 0x0F)))
        self._buf.write(b'\x00')   # reserved
        self._buf.write(b'\x00')   # architecture = 0x00 = little-endian
        self._buf.write(struct.pack('<H', global_num))
        self._buf.write(struct.pack('B', len(field_defs)))
        for field_id, size, base_type in field_defs:
            self._buf.write(struct.pack('BBB', field_id, size, base_type))

    def write_message(self, local_num: int, values: list) -> None:
        """Write a FIT data record.

        Args:
            local_num: Must match a previously defined local message number.
            values:    Pre-encoded bytes objects, one per field in definition order.
        """
        # Data header byte: bits 3–0 = local_num; no high bits set
        self._buf.write(struct.pack('B', local_num & 0x0F))
        for v in values:
            self._buf.write(v)

    def encode_value(self, value, base_type: int, size: int = None) -> bytes:
        """Encode a Python value to bytes for a given FIT base type.

        Args:
            value:     Python value to encode. None → type-specific invalid sentinel.
            base_type: FIT base type byte (key of BASE_TYPE_DEFINITIONS).
            size:      Override byte size. Required for STRING fields.
                       Defaults to BASE_TYPE_DEFINITIONS[base_type]['size'].

        Returns:
            Bytes of exactly `size` length in little-endian order.
        """
        bt = BASE_TYPE_DEFINITIONS[base_type]
        if size is None:
            size = bt['size']
        type_code = bt['type_code']

        if type_code == 's':  # STRING (base type 0x07)
            if value is None:
                return b'\x00' * size
            encoded = str(value).encode('utf-8')[:size - 1]  # leave 1 byte for null
            return encoded + b'\x00' * (size - len(encoded))

        if value is None:
            return struct.pack('<' + type_code, bt['invalid'])

        return struct.pack('<' + type_code, value)

    def get_bytes(self) -> bytes:
        """Finalise the FIT file.

        Backfills the 14-byte file header (including its own 2-byte CRC), then
        appends the 2-byte file CRC over the complete (header + data) region.

        Returns:
            Complete, valid FIT file bytes ready to write to a .fit file.
        """
        raw = self._buf.getvalue()
        data_bytes = raw[self.HEADER_SIZE:]
        data_size = len(data_bytes)

        # Build the 12-byte header body (without trailing 2-byte header CRC):
        #   offset 0  uint8   header_size = 14
        #   offset 1  uint8   protocol_version = 0x10
        #   offset 2  uint16  profile_version = 21188
        #   offset 4  uint32  data_size
        #   offset 8  4 bytes ".FIT" magic
        # Total: 1+1+2+4+4 = 12 bytes
        header_body = struct.pack(
            '<BBHI4s',
            self.HEADER_SIZE,
            self.PROTOCOL_VERSION,
            self.PROFILE_VERSION,
            data_size,
            b'.FIT',
        )

        header_crc = CrcCalculator.calculate_crc(header_body, 0, 12)
        full_header = header_body + struct.pack('<H', header_crc)  # 14 bytes

        # File CRC covers the entire file (header + data), NOT the trailing 2-byte CRC.
        full_file = full_header + data_bytes
        file_crc = CrcCalculator.calculate_crc(full_file, 0, len(full_file))

        return full_file + struct.pack('<H', file_crc)
