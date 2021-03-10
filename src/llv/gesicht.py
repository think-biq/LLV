"""    
    Serialization / Deserialization tool for ARKit face blendshapes as provided
    by Epic Games' Live Link iOS app.

    2021-∞ (c) blurryroots innovation qanat OÜ. All rights reserved.
    See license.md for details.

    https://think-biq.com
"""

import struct
import json
import base64


def remap(x, in_min, in_max, out_min, out_max):
  return min(in_max, (x - in_min)) * (out_max - out_min) / (in_max - in_min) + out_min

def fract(x):
    xi = int(x)
    return x - float(xi)


class FaceFrame:
    """
    Represents a ARKit face frame.
    """

    # Min and Max packet sizes in bytes.
    # See https://github.com/EpicGames/UnrealEngine/blob/2bf1a5b83a7076a0fd275887b373f8ec9e99d431/Engine/Plugins/Runtime/AR/AppleAR/AppleARKitFaceSupport/Source/AppleARKitFaceSupport/Private/AppleARKitLiveLinkSource.cpp#L256
    PACKET_MIN_SIZE = 264
    PACKET_MAX_SIZE = 774

    # Blendshape names:
    # See https://docs.unrealengine.com/en-US/API/Runtime/AugmentedReality/EARFaceBlendShape/index.html
    FACE_BLENDSHAPE_NAMES = [
        "EyeBlinkLeft",
        "EyeLookDownLeft",
        "EyeLookInLeft",
        "EyeLookOutLeft",
        "EyeLookUpLeft",
        "EyeSquintLeft",
        "EyeWideLeft",
        "EyeBlinkRight",
        "EyeLookDownRight",
        "EyeLookInRight",
        "EyeLookOutRight",
        "EyeLookUpRight",
        "EyeSquintRight",
        "EyeWideRight",
        "JawForward",
        "JawLeft",
        "JawRight",
        "JawOpen",
        "MouthClose",
        "MouthFunnel",
        "MouthPucker",
        "MouthLeft",
        "MouthRight",
        "MouthSmileLeft",
        "MouthSmileRight",
        "MouthFrownLeft",
        "MouthFrownRight",
        "MouthDimpleLeft",
        "MouthDimpleRight",
        "MouthStretchLeft",
        "MouthStretchRight",
        "MouthRollLower",
        "MouthRollUpper",
        "MouthShrugLower",
        "MouthShrugUpper",
        "MouthPressLeft",
        "MouthPressRight",
        "MouthLowerDownLeft",
        "MouthLowerDownRight",
        "MouthUpperUpLeft",
        "MouthUpperUpRight",
        "BrowDownLeft",
        "BrowDownRight",
        "BrowInnerUp",
        "BrowOuterUpLeft",
        "BrowOuterUpRight",
        "CheekPuff",
        "CheekSquintLeft",
        "CheekSquintRight",
        "NoseSneerLeft",
        "NoseSneerRight",
        "TongueOut",
        "HeadYaw",
        "HeadPitch",
        "HeadRoll",
        "LeftEyeYaw",
        "LeftEyePitch",
        "LeftEyeRoll",
        "RightEyeYaw",
        "RightEyePitch",
        "RightEyeRoll",
    ]

    @staticmethod
    def from_default(frame_number = 0):
        frame = FaceFrame()

        frame._write_uint8(6)
        frame._write_string('00000000-0000-0000-0000-000000000000')
        frame._write_string('LLV')
        sub_frame = frame_number * 0.000614 + 0.121
        frame._write_frametime({"frame_number":1337 + frame_number, "sub_frame":sub_frame, "numerator":60, "denominator":1})

        use_test_frame = False

        
        shapes = {}
        for name in FaceFrame.FACE_BLENDSHAPE_NAMES:
            shapes[name] = 0.0
        shapes['JawOpen'] = remap(fract(frame_number / 30), 0, 1, 0, 1)

        count = len(shapes)
        frame._write_uint8(count)
        for name in shapes:
            frame._write_float(shapes[name])

        frame.size = len(frame.data)

        frame._deserialize()

        return frame


    @staticmethod
    def from_json(frame_json):
        frame = FaceFrame()

        frame._write_uint8(frame_json['version'])
        frame._write_string(frame_json['device_id'])
        frame._write_string(frame_json['subject_name'])
        frame._write_frametime(frame_json['frame_time'])

        count = frame_json['blendshape_count']
        frame._write_uint8(count)
        for blendshape_name in frame_json['blendshapes']:
            frame._write_float(frame_json['blendshapes'][blendshape_name])

        frame.size = len(frame.data)

        frame._deserialize()

        return frame


    @staticmethod
    def from_raw(data, data_size):
        if data_size < FaceFrame.PACKET_MIN_SIZE:
            raise Exception(f"Trying to read frame ({data_size}) smaller than min size! ({FaceFrame.PACKET_MIN_SIZE})")
        if FaceFrame.PACKET_MAX_SIZE < data_size:
            raise Exception(f"Trying to read frame bigger than {FaceFrame.PACKET_MAX_SIZE} bytes!")

        #
        frame = FaceFrame()
        frame.data = data
        frame.size = data_size
        frame.current_position = 0

        frame._deserialize()

        return frame


    def __init__(self):
        self.data = b''
        self.size = 0
        self.current_position = 0

        self.version = 6
        self.device_id = 'None'
        self.subject_name = 'None'
        self.frame_time = {"frame_number":0, "sub_frame":0, "numerator":0, "denominator":0}

        self.blendshape_count = 0
        self.blendshapes = {}


    def _deserialize(self):
        # Read frame meta data.
        self.version = self._read_uint8()
        self.device_id = self._read_string()
        self.subject_name = self._read_string()
        self.frame_time = self._read_frametime()

        #
        self.blendshape_count = self._read_uint8()
        for blendshape_index in range(0, self.blendshape_count):
            blendshape_name = FaceFrame.FACE_BLENDSHAPE_NAMES[blendshape_index]
            self.blendshapes[blendshape_name] = self._read_float()

        unused_padding = self.size - self.current_position
        if 0 != unused_padding:
            print(f'Left over data after serialization! {self.current_position}/{self.size} => ({self.data[self.current_position:]})')
            self.data = self.data[:-unused_padding]
            self.size = len(self.data)


    def equals(self, other):
        version_ok = self.version == other.version
        if not version_ok:
            print(f'version differ: {self.version} != {other.version}')
        id_ok = self.device_id == other.device_id
        if not id_ok:
            print(f'device_id differ: {self.device_id} != {other.device_id}')
        subject_ok = self.subject_name == other.subject_name
        if not subject_ok:
            print(f'subject_name differ: {self.subject_name} != {other.subject_name}')
        frametime_ok = self.frame_time == other.frame_time
        if not frametime_ok:
            print(f'frame_time differ: {self.frame_time} != {other.frame_time}')
        blendshapes_ok = self.blendshapes == other.blendshapes
        if not blendshapes_ok:
            print(f'blendshapes differ: {self.blendshapes} != {other.blendshapes}')
        return version_ok and id_ok and frametime_ok and blendshapes_ok


    def to_json(self, with_shape_values = True, with_raw_frame = False):
        value = '{'
        value += f'"version":{json.dumps(self.version)}'
        value += f', "device_id":{json.dumps(self.device_id)}'
        value += f', "subject_name":{json.dumps(self.subject_name)}'
        value += f', "frame_time":{json.dumps(self.frame_time)}'
        value += f', "blendshape_count":{json.dumps(self.blendshape_count)}'
        if with_shape_values:
            value += f', "blendshapes": {json.dumps(self.blendshapes)}'
        if with_raw_frame:
            value += f', "raw_frame": {{ "size": {self.size}, "data": {json.dumps(base64.b64encode(self.data).decode())} }}'

        value += '}'

        return value


    def __str__(self):
        return self.to_json()


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


    def _raise_if_invalid(self):        
        if not self._is_valid():
            raise Exception(f"FaceFrame invalid! (current_position:{self.current_position}, size:{self.size})")


    def _is_valid(self):
        return 0 < self.size \
            and -1 < self.current_position \
            and self.current_position < self.size


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


    def _read_frametime(self):
        # The value of the frame number
        frame_number = self._read_int32()
        # ??
        sub_frame = self._read_float()
        # The numerator of the framerate represented as a number of frames per second (e.g. 60 for 60 fps)
        numerator = self._read_int32()
        # The denominator of the framerate represented as a number of frames per second (e.g. 1 for 60 fps)
        denominator = self._read_int32()
        return {"frame_number":frame_number, "sub_frame":sub_frame, "numerator":numerator, "denominator":denominator}

    def _write_frametime(self, value):
        bytes_written = 0
        bytes_written += self._write_int32(value['frame_number'])
        bytes_written += self._write_float(value['sub_frame'])
        bytes_written += self._write_int32(value['numerator'])
        bytes_written += self._write_int32(value['denominator'])
        return bytes_written
