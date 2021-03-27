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
import struct
import os
import gzip
import csv
import math
from .gesicht import FaceFrame, remap
from .buchse import Buchse
from .__init__ import version as get_version


def tween(a, b, frames):
    if 2 > frames:
        return [b]
    diff = b - a
    step = diff / (frames - 1)
    return [a + i * step for i in range(0, frames)]


def clamp(value, min_value, max_value):
   return max(min(value, max_value), min_value)


def is_binary_file(file_name):
    """
    Tries to open file in text mode and read first 64 bytes. If it fails,
    we can be fairly certain, this is due to the file being binary encoded.
    Thanks Sehrii https://stackoverflow.com/a/51495076/949561 for the help.
    """
    try:
        with open(file_name, 'tr') as check_file:
            check_file.read(32)
            return False
    except:
        return True


def _read_frames_json(filepath):
    with open(filepath, 'r', encoding='utf-8', newline='\r\n') as f:
        recording_json = json.load(f)

        frame_count = recording_json['count']
        frame_index = 0

        for frame_json in recording_json['frames']:
            yield frame_json, frame_index, frame_count, frame_json['version']
            frame_index += 1


def _read_frames_binary(filepath):
    file_size = os.path.getsize(filepath)
    with gzip.open(filepath, 'rb') as file:
        version, = struct.unpack('>B', file.read(1))
        if version != FaceFrame.VERSION:
            raise Exception(f'Incompatible frame versions! Recording is at {version}, llv at {FaceFrame.VERSION}.')
        frame_count, = struct.unpack('>L', file.read(4))

        for frame_index in range(0, frame_count):
            raw_frame_size = file.read(4)
            frame_size, = struct.unpack('>L', raw_frame_size)
            frame_data = file.read(frame_size)

            yield frame_data, frame_index, frame_count, version

        file_pos = file.tell()
        if file_pos < file_size:
            raise Exception(f'Recording seems corrupted! Data after last frame! {file_pos}/{file_size}')


def read_frames(filepath, loop = False):
    is_binary = is_binary_file(filepath)
    keep_reading = True
    while keep_reading:
        if is_binary:
            frame_generator = _read_frames_binary(filepath)
        else:
            frame_generator = _read_frames_json(filepath)
        
        for frame_package in frame_generator:
            yield frame_package

        keep_reading = loop


def playback(host, port, filepath, fps, loop = True):
    fps = clamp(fps, 1, 76) # https://stackoverflow.com/a/1133888

    sleep_time = 1/fps

    buchse = Buchse(host, port, as_server = False)
    print(f'Establish connection ({buchse.connection_info}) ...')

    frame_index = -1
    frame_count = -1
    for frame_package in read_frames(filepath, loop=loop):
        frame_data, frame_index, frame_count, version = frame_package
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


def pack(clear_filepath, output, rename = ''):
    print(f'Generating packed recording at {clear_filepath} from clearfile {clear_filepath} ...')
    with gzip.open(output, 'wb') as outfile:
        outfile.write(struct.pack('>B', FaceFrame.VERSION)) # version of the binary protocol

        for frame_json, frame_index, frame_count, version in read_frames(clear_filepath, is_binary = False, loop = False):
            if 0 == frame_index:
                # how many frames are in the recording?
                outfile.write(struct.pack('>L', frame_count))

            if 0 < len(rename):
                frame_json['subject_name'] = rename
                frame_json['device_id'] = 'DEADC0DE-1337-1337-1337-CAFEBABE'

            frame = FaceFrame.from_json(frame_json)
            outfile.write(frame.encode())

    print(f'Done.')


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


def create_modifier(output_path, default_value = 1.0):
    modifiers = {}
    for shape_name in FaceFrame.FACE_BLENDSHAPE_NAMES:
        modifiers[shape_name] = default_value

    with open(output_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(json.dumps(modifiers))


def apply_modifiers(recording_filepath, modifiers_filepath, default_value = 1.0):
    is_binary_recording = is_binary_file(recording_filepath)
    for frame_data, frame_index, frame_count, version \
        in read_frames(recording_filepath, is_binary = is_binary_recording, loop = False):
        raise Exception('Not implemented yet!')


def create_remap_library(csv_filepath, library_filepath, dialect = 'excel'):
    mapping = {}
    modifiers = {}
    reverse_mapping = {}
    with open(csv_filepath, 'r') as f:
        index = -1
        for row in csv.reader(f, dialect='excel'):
            index += 1
            if 0 == index:
                continue
            if 'undefined' in row[1].lower():
                continue
            if 'undefined' in row[2].lower():
                continue
            mapping[row[1]] = row[2]
            modifiers[row[1]] = float(row[3])
            reverse_mapping[row[2]] = row[1]

    result = {'mapping': mapping, 'modifiers': modifiers, 'reverse': reverse_mapping}

    with open(library_filepath, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(json.dumps(result))


def fbx_list(fbx_meta_filepath):
    with open(fbx_meta_filepath, 'r', encoding='utf-8', newline='\r\n') as f:
        fbx_metadata = json.load(f)
        for shape in fbx_metadata['shapes']:
            print(shape['target'])


def fbx_meta(fbx_meta_filepath, library_filepath, output_path):
    library = None
    with open(library_filepath, 'r', encoding='utf-8', newline='\r\n') as f:
        library = json.load(f)

    arr = {}
    for key in library['reverse'].keys():
        arr[key.lower()] = key

    shape_values = {}
    for shape_name in FaceFrame.FACE_BLENDSHAPE_NAMES:
        shape_values[shape_name] = []

    max_duration = 0
    max_len_values = 0
    with open(fbx_meta_filepath, 'r', encoding='utf-8', newline='\r\n') as f:
        fbx_metadata = json.load(f)
        for shape in fbx_metadata['shapes']:
            l = shape['target'].lower()
            if l in arr:
                arkit_name = library['reverse'][arr[l]]
                mesh_name = arr[l]
                shape_values[arkit_name] = [
                    library['modifiers'][arkit_name] * value for value in shape['curves'][0]['values']
                ]
                max_len_values = max(max_len_values, len(shape_values[arkit_name]))
                max_duration = max(max_duration, shape['curves'][0]['end_time'] - shape['curves'][0]['start_time'])

    tween_frames = math.floor(60.0 / math.floor(max_len_values / max_duration))
    if 1 > tween_frames:
        raise Exception(f'Weirdness! 1 > (60 / ({max_len_values} (max_len_values) / {max_duration} (max_duration)))')

    for name in shape_values:
        if max_len_values != len(shape_values[name]):
            shape_values[name] = [0] * max_len_values
        raw = shape_values[name]
        raw_length = len(raw)
        shape_values[name] = []
        previous_value = -1
        for i in range(0, raw_length):
            if 0 == i:
                previous_value = raw[i]
                continue
            shape_values[name] += tween(previous_value, raw[i], tween_frames)
            previous_value = raw[i]

    options = {'duration': max_duration
        , 'samples': max_len_values
        , 'fps': 60
        , 'tweens': tween_frames}

    print(f'Options: {options}')

    total_number_of_frames = (options['samples']-1) * options['tweens']
    print(f'Processing {total_number_of_frames} frames ...')
    with open(output_path, 'w', encoding='utf-8', newline='\r\n') as file:
        file.write(f'{{"count": {total_number_of_frames}, "frames": [')
        for frame_index in range(0, total_number_of_frames):
            frame = FaceFrame.from_default(frame_index)
            for shape_name in FaceFrame.FACE_BLENDSHAPE_NAMES:
                shape_value = 0
                if shape_name in shape_values:
                    try:
                        shape_value = shape_values[shape_name][frame_index]
                    except Exception as e:
                        print(f'Got {e} when accessing {frame_index} / len {len(shape_values[shape_name])}')
                        raise e
                frame.blendshapes[shape_name] = shape_value

            file.write(frame.to_json())

            if frame_index < (total_number_of_frames - 1):
                file.write(',')

        file.write(']}')
        

def create_arg_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    # Setup global flags for verbosity level and version print.
    parser.add_argument('-v', '--verbose'
        , action='store_true'
        , help='Activate verbose logging.'
        , default=False)
    parser.add_argument('-V', '--version'
        , action='store_true'
        , help='Show version number.'
        , default=False)

    # Split object for subparsers.
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

    remap_args = subparsers.add_parser('remap')
    remap_args.add_argument('csv_filepath', metavar='csv_filepath', type=str
        , help='Path to csv file with remapping info.')
    remap_args.add_argument('output_path', metavar='out_path', type=str
        , help='Path to write mapping file to.')
    remap_args.add_argument('--dialect', metavar='d', type=str
        , help='Dialect used in csv file.'
        , default='excel')

    remap_args = subparsers.add_parser('fbx')
    remap_args.add_argument('fbx_meta_filepath', metavar='fbx_meta_filepath', type=str
        , help='Path to fbx blendshape metadata file.')
    remap_args.add_argument('library_filepath', metavar='library_filepath', type=str
        , help='Path to blendshape mapping definition file.')
    remap_args.add_argument('output_path', metavar='out_path', type=str
        , help='Path to write llv recording file to.')

    remap_args = subparsers.add_parser('fbx-list')
    remap_args.add_argument('fbx_meta_filepath', metavar='fbx_meta_filepath', type=str
        , help='Path to fbx blendshape metadata file.')

    return parser


def main():
    parser = create_arg_parser()
    args = parser.parse_args()

    if args.version:
        print(get_version())
        sys.exit(0)

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
    elif 'remap' == args.command:
        create_remap_library(args.csv_filepath, args.output_path, args.dialect)
    elif 'fbx' == args.command:
        fbx_meta(args.fbx_meta_filepath, args.library_filepath, args.output_path)
    elif 'fbx-list' == args.command:
        fbx_list(args.fbx_meta_filepath)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()