"""    
    Generic serialization / deserialization utility.

    2021-∞ (c) blurryroots innovation qanat OÜ. All rights reserved.
    See license.md for details.

    https://think-biq.com
"""

class Tape():

	def __init__(self):
		self.data = b''
		self.size = 0
		self.current_position = 0


    def _read_raw_slice(self, data_size):
        self._raise_if_invalid()
        data_start = self.current_position
        data_end = self.current_position + data_size
        if not (data_end <= self.size):
            raise Exception(f"Trying to access beyond package size! data_end:{data_end}, size:{self.size}")
        data_slice = self.data[data_start:data_end]
        self.current_position = data_end
        return data_slice


    def _write_raw_slice(self, data):
        slice_size = len(data)
        self.data += data
        self.size += slice_size
        return slice_size


    def _read_uint8(self):
        data_slice = self._read_raw_slice(1)
        value, = struct.unpack(">B", data_slice)
        return value

    def _write_uint8(self, value):
        data_slice = struct.pack('>B', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_uint32(self):
        data_slice = self._read_raw_slice(4)
        value, = struct.unpack('>L', data_slice)
        return value

    def _write_uint32(self, value):
        data_slice = struct.pack('>L', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_int32(self):
        data_slice = self._read_raw_slice(4)
        value, = struct.unpack(">l", data_slice)
        return value

    def _write_int32(self, value):
        data_slice = struct.pack('>l', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_float(self):
        data_slice = self._read_raw_slice(4)
        value, = struct.unpack(">f", data_slice)
        return value

    def _write_float(self, value):
        data_slice = struct.pack('>f', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_string(self):
        string_length = self._read_int32()
        bytes_left = self.size - self.current_position
        is_length_ok = (0 <= string_length) and (string_length <= bytes_left)
        if not is_length_ok:
            raise Exception(f"Read invalid string length! (str_l:{string_length}, bytes_left:{bytes_left})")
        data_slice = self._read_raw_slice(string_length)
        value, = struct.unpack(f">{string_length}s", data_slice)
        return value.decode('utf8')

    def _write_string(self, value):
        string_bytes = value.encode('utf8')
        string_bytes_length = len(string_bytes)
        self._write_int32(string_bytes_length)
        data_slice = struct.pack(f'>{string_bytes_length}s', string_bytes)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_uint8(self):
        data_slice = self._read_raw_slice(1)
        value, = struct.unpack(">B", data_slice)
        return value

    def _write_uint8(self, value):
        data_slice = struct.pack('>B', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_uint32(self):
        data_slice = self._read_raw_slice(4)
        value, = struct.unpack('>L', data_slice)
        return value

    def _write_uint32(self, value):
        data_slice = struct.pack('>L', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_int32(self):
        data_slice = self._read_raw_slice(4)
        value, = struct.unpack(">l", data_slice)
        return value

    def _write_int32(self, value):
        data_slice = struct.pack('>l', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_float(self):
        data_slice = self._read_raw_slice(4)
        value, = struct.unpack(">f", data_slice)
        return value

    def _write_float(self, value):
        data_slice = struct.pack('>f', value)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written


    def _read_string(self):
        string_length = self._read_int32()
        bytes_left = self.size - self.current_position
        is_length_ok = (0 <= string_length) and (string_length <= bytes_left)
        if not is_length_ok:
            raise Exception(f"Read invalid string length! (str_l:{string_length}, bytes_left:{bytes_left})")
        data_slice = self._read_raw_slice(string_length)
        value, = struct.unpack(f">{string_length}s", data_slice)
        return value.decode('utf8')

    def _write_string(self, value):
        string_bytes = value.encode('utf8')
        string_bytes_length = len(string_bytes)
        self._write_int32(string_bytes_length)
        data_slice = struct.pack(f'>{string_bytes_length}s', string_bytes)
        bytes_written = self._write_raw_slice(data_slice)
        return bytes_written