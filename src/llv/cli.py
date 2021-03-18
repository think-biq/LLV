"""    
    Virtual Object MItigation Tool

    2021-∞ (c) blurryroots innovation qanat OÜ. All rights reserved.
    See license.md for details.

    https://think-biq.com
"""

import sys
import time
import argparse
import json
import base64
from .gesicht import FaceFrame, remap
from .buchse import Buchse
import struct
import os
import gzip

def clamp(value, min_value, max_value):
   return max(min(value, max_value), min_value)


def read_frames(filepath, loop = False):
    file_size = os.path.getsize(filepath)

    keep_reading = True
    while keep_reading:
        with gzip.open(filepath, 'rb') as file:
            file.seek(0, 0)

            version, = struct.unpack('>B', file.read(1))
            if version != FaceFrame.VERSION:
                raise Exception(f'Incompatible frame versions! Recording is at {version}, llv at {FaceFrame.VERSION}.')
            frame_count, = struct.unpack('>L', file.read(4))

            for frame_index in range(0, frame_count):
                raw_frame_size = file.read(4)
                frame_size, = struct.unpack('>L', raw_frame_size)
                frame_data = file.read(frame_size)

                yield frame_data, frame_index, frame_count, version

        if not loop:
            keep_reading = False


def playback(host, port, filepath, fps, loop = True):
    fps = clamp(fps, 1, 76) # https://stackoverflow.com/a/1133888

    sleep_time = 1/fps

    buchse = Buchse(host, port, as_server = False)
    print(f'Establish connection ({buchse.connection_info}) ...')

    frame_index = -1
    frame_count = -1
    for frame_data, frame_index, frame_count, version in read_frames(filepath, loop):
        if 0 == frame_index:
            print(f'Start sending {frame_count} frames of version {version} @{fps}fps ...')

        frame = FaceFrame.from_raw(frame_data, len(frame_data))

        bytes_sent = buchse.sprech(frame.data, frame.size)
        if bytes_sent != frame.size:
            raise Exception(f'Error sending full frame! ({bytes_sent}/{frame.size})')

        try:
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            print('Stopping playback ...')
            break

    return frame_index, frame_count


def record(host, port, frames, output, with_raw_frame = False):
    sleep_time = 1/76 # https://stackoverflow.com/a/1133888
    buchse = Buchse(host, port, as_server = True)

    print(f'Waiting for {frames} frames to write ...')

    with gzip.open(output, 'wb') as file:
        file.write(struct.pack('>B', FaceFrame.VERSION)) # version of the binary protocol
        file.write(struct.pack('>L', frames)) # how many frames are in the recording?

        current_data_frame = 0
        while current_data_frame < frames:
            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                print('Stopping playback ...')
                break

            data, size = buchse.horch(FaceFrame.PACKET_MAX_SIZE)
            if not data or 0 == size:
                print(f'Received empty frame, skipping ...')
                continue

            try:
                frame = FaceFrame.from_raw(data, size)
            except Exception as e:
                print(f'Encountered: {e}')
                print(f'Skipping frame ...')
                continue

            print(f'Processing frame {current_data_frame+1} ({frame.frame_time["frame_number"]}) ...')

            frame_packet = frame.encode()
            file.write(frame_packet)

            current_data_frame += 1

    return current_data_frame, frames, output


def unpack(raw_file, output, retain_raw_frame = True, rename = ''):
    with open(output, 'w', encoding='utf-8', newline='\r\n') as file:
        frame_index = -1
        frame_count = -1
        for frame_data, frame_index, frame_count, version in read_frames(raw_file, loop = False):
            if 0 == frame_index:
                file.write(f'{{"count": {frame_count}, "frames": [')

            frame = FaceFrame.from_raw(frame_data, len(frame_data))

            if 0 < len(rename):
                frame.subject_name = rename
                frame.device_id = 'DEADC0DE-1337-1337-1337-CAFEBABE'

            file.write(frame.to_json(with_raw_frame = retain_raw_frame))

            if frame_index < (frame_count - 1):
                file.write(',')

        file.write(']}')


def pack(clear_file, output, rename = ''):
    with gzip.open(output, 'wb') as outfile:
        outfile.write(struct.pack('>B', FaceFrame.VERSION)) # version of the binary protocol

        recording_json = None
        with open(clear_file, 'r', encoding='utf-8', newline='\r\n') as infile:
            recording_json = json.load(infile)

        outfile.write(struct.pack('>L', recording_json['count'])) # how many frames are in the recording?

        for frame_json in recording_json['frames']:
            if 0 < len(rename):
                frame_json['subject_name'] = rename
                frame_json['device_id'] = 'DEADC0DE-1337-1337-1337-CAFEBABE'
            frame = FaceFrame.from_json(frame_json)
            outfile.write(frame.encode())


def migrate(legacy_file, output, rename = ''):
    with gzip.open(output, 'wb') as outfile:
        outfile.write(struct.pack('>B', FaceFrame.VERSION)) # version of the binary protocol

        line_count = 0
        with open(legacy_file, 'r', encoding='utf-8', newline='\r\n') as infile:
            for _ in infile.readlines():
                line_count += 1

            outfile.write(struct.pack('>L', line_count)) # how many frames are in the recording?

        print(f'Processing {line_count} legacy frames ...')

        with open(legacy_file, 'r', encoding='utf-8', newline='\r\n') as infile:
            line_index = 0
            for l in infile.readlines():
                line_index += 1

                decoded_line = base64.b64decode(l)
                decoded_line_string = decoded_line.decode('utf8')
                frame_json = json.loads(decoded_line_string)

                if 0 < len(rename):
                    frame_json['subject_name'] = rename
                    frame_json['device_id'] = 'DEADC0DE-1337-1337-1337-CAFEBABE'

                frame = FaceFrame.from_json(frame_json)
                outfile.write(frame.encode())



def _write_frames_for_shape(file, shape_name, frames_per_shape, total_number_of_shapes, min_value = -1.0, max_value = 1.0):
    shape_index = 0
    for shape_frame_index in range(0, frames_per_shape):
        frame_index = shape_index*total_number_of_shapes + shape_frame_index

        frame = FaceFrame.from_default(frame_index)
        frame.blendshapes[shape_name] = remap(shape_frame_index, 0, frames_per_shape-1, min_value, max_value)

        file.write(frame.encode())

def sequence(output, time_per_shape = 1.1, fps = 60, single_shape = '', min_value = -1.0, max_value = 1.0):
    print(f'Requesting debug sequence with {time_per_shape}s per shape @{fps}fps ...')

    frames_written = 0
    frames_per_shape = max(1, round(fps * time_per_shape))

    total_number_of_shapes = 1 if 0 < len(single_shape) else len(FaceFrame.FACE_BLENDSHAPE_NAMES)
    total_number_of_frames = int(total_number_of_shapes * frames_per_shape)

    print(f'Creating {output} with a total of {total_number_of_frames}')

    with gzip.open(output, 'wb') as file:
        file.write(struct.pack('>B', FaceFrame.VERSION)) # version of the binary protocol
        file.write(struct.pack('>L', total_number_of_frames)) # how many frames are in the recording?

        if 0 < len(single_shape):
            print(f'Preparing animtion of a single shape ({single_shape}) ...')
            if not single_shape in FaceFrame.FACE_BLENDSHAPE_NAMES:
                raise Exception(f'Could not find {single_shape} in shape blendshape defintion!')
            _write_frames_for_shape(file, single_shape, frames_per_shape, total_number_of_shapes, min_value, max_value)
        else:
            print(f'Preparing sequence of all available shapes ...')
            for shape_index in range(0, total_number_of_shapes):
                shape_name = FaceFrame.FACE_BLENDSHAPE_NAMES[shape_index]
                _write_frames_for_shape(file, shape_name, frames_per_shape, total_number_of_shapes, min_value, max_value)

    return frames_written


def create_arg_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='command')

    # Setup record command and options.
    record_args = subparsers.add_parser('record')
    record_args.add_argument('--host', metavar='h', type=str
        , help='Host address to bind (0.0.0.0 by default).'
        , default='')
    record_args.add_argument('--port', metavar='p', type=int
        , help='Port to host server on.'
        , default=11111)
    record_args.add_argument('--frames', metavar='f', type=int
        , help='Frame count to record.'
        , default=300)
    record_args.add_argument('--with-raw'
        , action='store_true'
        , help='Flag to configure if recording should retain raw binary network frame. (false by default)'
        , default=False)
    record_args.add_argument('--output', metavar='o', type=str
        , help='Path where recording is stored.'
        , default=f'./recording-{time.strftime("%Y-%m-%d-%H-%M-%S")}.gesichter')

    # Setup play command and options.
    play_args = subparsers.add_parser('play')
    play_args.add_argument('recording_path', metavar='in_path', type=str
        , help='Path to recording file.')
    play_args.add_argument('--fps', metavar='f', type=float
        , help='Playback speed for animation frames.'
        , default=60)
    play_args.add_argument('--host', metavar='h', type=str
        , help='Target host to send data to.'
        , default='localhost')
    play_args.add_argument('--port', metavar='p', type=int
        , help='Port to target.'
        , default=11111)

    # Setup unpack command and options.
    unpack_args = subparsers.add_parser('unpack')
    unpack_args.add_argument('recording_path', metavar='in_path', type=str
        , help='Path to a raw recording file.')
    unpack_args.add_argument('output_path', metavar='out_path', type=str
        , help='Path where unpacked recording is stored.')
    unpack_args.add_argument('--retain'
        , help='Retains original raw frame data. (false by default)'
        , action='store_true'
        , default=False)
    unpack_args.add_argument('--rename', metavar='n', type=str
        , help='Rename subject name and anonymizes device id.'
        , default='')

    # Setup pack command and options.
    pack_args = subparsers.add_parser('pack')
    pack_args.add_argument('clearfile_path', metavar='in_file', type=str
        , help='Path to a recording clearfile.')
    pack_args.add_argument('output_path', metavar='out_file', type=str
        , help='Path where unpacked recording is stored.')
    pack_args.add_argument('--rename', metavar='n', type=str
        , help='Rename subject name and anonymizes device id.'
        , default='')

    # Setup pack command and options.
    migrate_args = subparsers.add_parser('migrate')
    migrate_args.add_argument('legacy_file', metavar='in_file', type=str
        , help='Path to a recording clearfile.')
    migrate_args.add_argument('output_path', metavar='out_file', type=str
        , help='Path where unpacked recording is stored.')
    migrate_args.add_argument('--rename', metavar='n', type=str
        , help='Rename subject name and anonymizes device id.'
        , default='')

    debug_args = subparsers.add_parser('sequence')
    debug_args.add_argument('output_path', metavar='out_file', type=str
        , help='Path where unpacked recording is stored.')
    debug_args.add_argument('--time-per-shape', metavar='t', type=float
        , help='Time duration for each shape to show its max value.'
        , default=1.0)
    debug_args.add_argument('--single-shape', metavar='s', type=str
        , help='Only animates the specific shape in this sequence.'
        , default='')    
    debug_args.add_argument('--min', metavar='v', type=float
        , help='Minimum value for the shape to assume when animating.'
        , default=-1.0)
    debug_args.add_argument('--max', metavar='v', type=float
        , help='Maximum value for the shape to assume when animating.'
        , default=1.0)

    return parser


def main():
    parser = create_arg_parser()
    args = parser.parse_args()

    if 'play' == args.command:
        frames_read, frames_total = playback(args.host, args.port, args.recording_path, args.fps)
        print(f'Stopped at frame {frames_read}/{frames_total}')
    elif 'record' == args.command:
        frames_read, frames_requested, filepath = record(args.host, args.port, args.frames, args.output, args.with_raw)
        print(f'Stopped at frame {frames_read}/{frames_requested}, written file to {filepath}')
    elif 'unpack' == args.command:
        unpack(args.recording_path, args.output_path, args.retain, args.rename)
    elif 'pack' == args.command:
        pack(args.clearfile_path, args.output_path, args.rename)
    elif 'migrate' == args.command:
        migrate(args.legacy_file, args.output_path, args.rename)
    elif 'sequence' == args.command:
        fps = 60
        sequence(args.output_path, args.time_per_shape, fps, args.single_shape, args.min, args.max)
    else:
        parser.print_help()
        sys.exit(1)

    print('Shutting down ...')


if __name__ == '__main__':
    main()