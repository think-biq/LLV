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
from .gesicht import FaceFrame
from .buchse import Buchse


def clamp(value, min_value, max_value):
   return max(min(value, max_value), min_value)


def decode_raw_frame(frame_json):
    # raw_frame = base64.b64decode(frame_json['raw_frame']['data'].encode('utf8'))
    # raw_frame_size = frame_json['raw_frame']['size']
    frame = FaceFrame.from_json(frame_json)
    return frame


def encode_frame(frame_json):
    return base64.b64encode(frame_json.encode("utf8")).decode("utf8")


def read_frames(filepath, loop = False):
    frame_index = 0
    frames = 0

    with open(filepath, 'r', encoding='utf-8', newline='\r\n') as file:
        for l in file.readlines():
            frames += 1

        keep_sending = True
        while keep_sending:
            file.seek(0)
            for l in file.readlines():
                raw_json_string = base64.b64decode(l).decode('utf8')
                frame_json = json.loads(raw_json_string)

                yield frame_json, frame_index, frames

                frame_index += 1
                frame_index = frame_index if frame_index < frames else 0

            if not loop:
                keep_sending = False


def playback(host, port, filepath, fps, loop = True):
    fps = clamp(fps, 1, 76) # https://stackoverflow.com/a/1133888

    sleep_time = 1/fps

    buchse = Buchse(host, port, as_server = False)
    print(f'Establish connection ({buchse.connection_info}) ...')

    frame_index = -1
    frame_count = -1
    for frame_json, frame_index, frame_count in read_frames(filepath, loop):
        if 0 == frame_index:
            print(f'Start sending {frame_count} frames @{fps}fps ...')

        frame = FaceFrame.from_json(frame_json)
        #frame = FaceFrame.from_default(frame_index)

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

    with open(output, 'w', encoding='utf-8', newline='\r\n') as file:
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
            frame_json = frame.to_json(with_raw_frame = with_raw_frame)
            file.write(f'{encode_frame(frame_json)}\n')

            current_data_frame += 1

    return current_data_frame, frames, output


def unpack(raw_file, output, retain_raw_frame = True, rename = ''):
    with open(output, 'w', encoding='utf-8', newline='\r\n') as file:
        frame_index = -1
        frame_count = -1
        for frame, frame_index, frame_count in read_frames(raw_file):
            if 0 == frame_index:
                file.write(f'{{"count": {frame_count}, "frames": [')

            if not retain_raw_frame and 'raw_frame' in frame:
                del frame['raw_frame']
            if 0 < len(rename):
                frame['subject_name'] = rename
                frame['device_id'] = 'DEADC0DE-1337-1337-1337-CAFEBABE'
            file.write(json.dumps(frame))

            if frame_index < (frame_count - 1):
                file.write(',')

        file.write(']}')

# TODO: create raw frame form actual json!
def pack(clear_file, output, rename = ''):
    with open(output, 'w', encoding='utf-8', newline='\r\n') as outfile:
        recording_json = None
        with open(clear_file, 'r', encoding='utf-8', newline='\r\n') as infile:
            recording_json = json.load(infile)
            for frame in recording_json['frames']:
                if 0 < len(rename):
                    frame['subject_name'] = rename
                    frame['device_id'] = 'DEADC0DE-1337-1337-1337-CAFEBABE'
                frame_dump = json.dumps(frame)
                outfile.write(f'{encode_frame(frame_dump)}\n')


def produce_debug_sequence(output, time_per_shape = 1.1, fps = 60):
    frames_written = 0
    frames_per_shape = min(1, round(fps * time_per_shape))

    total_number_of_shapes = len(FaceFrame.FACE_BLENDSHAPE_NAMES)
    total_number_of_frames = int(total_number_of_shapes * frames_per_shape)
    for frame_index in range(0, total_number_of_frames):
        shape_index = int(frame_index % total_number_of_shapes)
        shape_name = FaceFrame.FACE_BLENDSHAPE_NAMES[shape_index]

        frame = FaceFrame.from_default(frame_index)
        frame.blendshapes[shape_name] = 1.0

    print('Not yet implemented :/')
    return frames_written


def create_arg_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='command')

    # Setup record command and options.
    record_args = subparsers.add_parser('record')
    record_args.add_argument('--host', metavar='host', type=str
        , help='Host address to bind (0.0.0.0 by default).'
        , default='')
    record_args.add_argument('--port', metavar='port', type=int
        , help='Port to host server on.'
        , default=11111)
    record_args.add_argument('--frames', metavar='frames', type=float
        , help='Frame count to record.'
        , default=300)
    record_args.add_argument('--with-raw'
        , action='store_true'
        , default=False)
    record_args.add_argument('--output', metavar='output', type=str
        , help='Path where recording is stored.'
        , default=f'./recording-{time.strftime("%Y-%m-%d-%H-%M-%S")}.gesichter')

    # Setup play command and options.
    play_args = subparsers.add_parser('play')
    play_args.add_argument('recording_path', metavar='recording_path', type=str
        , help='Path to recording file.')
    play_args.add_argument('--fps', metavar='fps', type=float
        , help='Playback speed for animation frames.'
        , default=60)
    play_args.add_argument('--host', metavar='host', type=str
        , help='Target host to send data to.'
        , default='localhost')
    play_args.add_argument('--port', metavar='port', type=int
        , help='Port to target.'
        , default=11111)

    # Setup unpack command and options.
    unpack_args = subparsers.add_parser('unpack')
    unpack_args.add_argument('recording_path', metavar='recording_path', type=str
        , help='Path to a raw recording file.')
    unpack_args.add_argument('output_path', metavar='output_path', type=str
        , help='Path where unpacked recording is stored.')
    unpack_args.add_argument('--retain'
        , help='Retains original raw frame data.'
        , action='store_true'
        , default=False)
    unpack_args.add_argument('--rename', metavar='rename', type=str
        , help='Rename subject name and anonymizes device id.'
        , default='')

    # Setup pack command and options.
    pack_args = subparsers.add_parser('pack')
    pack_args.add_argument('clearfile_path', metavar='clearfile_path', type=str
        , help='Path to a recording clearfile.')
    pack_args.add_argument('output_path', metavar='output_path', type=str
        , help='Path where unpacked recording is stored.')
    pack_args.add_argument('--rename', metavar='rename', type=str
        , help='Rename subject name and anonymizes device id.'
        , default='')

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
    elif 'produce_debug_sequence' == args.command:
        produce_debug_sequence(args.output_path, args.time_per_shape)
    else:
        parser.print_help()
        sys.exit(1)

    print('Shutting down ...')


if __name__ == '__main__':
    main()