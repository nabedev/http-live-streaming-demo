import time
import uuid
from pathlib import Path

import cv2
import m3u8
from m3u8.model import Segment
import ffmpeg
import ffmpy
import subprocess


DEVICE_ID = 0
FPS = 10
CODECS = 'mp4v'
CAPTURE_DURATION = 10


def main():
    vc = cv2.VideoCapture(DEVICE_ID)
    # HACK: opencvが30FPSで書き出してくれない。
    # fps = vc.get(cv2.CAP_PROP_FPS)
    width = int(vc.get(3))
    height = int(vc.get(4))

    video_filepath = 'video/{}.mp4'.format(uuid.uuid4())
    fourcc = cv2.VideoWriter_fourcc(*CODECS)
    writer = cv2.VideoWriter(
        filename=video_filepath,
        fourcc=fourcc,
        fps=FPS,
        frameSize=(width, height)
    )

    start_time = time.time()
    while(vc.isOpened()):
        if time.time() - start_time > CAPTURE_DURATION:
            writer.release()
            segment = generate_segment(video_filepath)
            update_playlist(segment)

            video_filepath = 'video/{}.mp4'.format(uuid.uuid4())
            writer = cv2.VideoWriter(video_filepath, fourcc, FPS, (width, height))
            start_time = time.time()

        ret, frame = vc.read()
        if ret is True:
            writer.write(frame)

            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break

    vc.release()
    writer.release()
    cv2.destroyAllWindows()


def generate_segment(filepath):
    """
    Args:
        filepath: input video filepath
    Return:
        Segm    ent object
    """
    # segment_filepath = 'output/{}'.format(uuid.uuid4())
    filename = Path(filepath).name
    segment_filepath = f'output/{filename}'

    # NOTE: ffmpeg-pythonをやめてsubprocessでやる。
    # セグメントのサイズを知る必要がある。ffmpeg-pythonのm3u8に記述されるが1ファイル。
    # subprocess.run(
    #     f'ffmpeg -i {filepath} -vcodec libx264 -movflags faststart -vprofile baseline -level 3.0 -g 150 -b:v 519k -s 768x432 -acodec libfdk_aac -b:a 63.4k -ar 44100 -flags +loop-global_header -map 0 -bsf h264_mp4toannexb -f segment -segment_format mpegts -segment_time 10 -segment_list segment.m3u8 segment.ts',
    #     shell=True
    # )

    # return m3u8.load(f'{segment_filepath}.m3u8').segments[0]

    # HACK: segmentが複数作成された場合に対応する必要がある。
    input_stream = ffmpeg.input(filepath, f='mp4')
    output_stream = ffmpeg.output(input_stream, f'{segment_filepath}.m3u8', format='hls', hls_time=10, hls_list_size=3)
    ffmpeg.run(output_stream)

    playlist = m3u8.load(f'{segment_filepath}.m3u8')
    return playlist.segments[0]

    # ff = ffmpy.FFmpeg(
    #     inputs={filepath: None},
    #     outputs={segment_filepath: None},
    # )
    # ff.run()

    # return Segment(
    #     uri=segment_filepath,
    #     base_uri='',
    #     duration=CAPTURE_DURATION,  # TODO: 実際の長さにする
    # )


def update_playlist(segment):
    playlist = m3u8.load('playlist.m3u8')
    segment.uri = f'output/{segment.uri}'
    playlist.segments.append(segment)

    # Keep up to 3 segment files
    # https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/StreamingMediaGuide/FrequentlyAskedQuestions/FrequentlyAskedQuestions.html#//apple_ref/doc/uid/TP40008332-CH103-SW1
    if (len(playlist.segments) > 3):
        playlist.segments.pop(0)

    # Update #EXT-X-TARGETDURATION config
    max_segment_duration = max([segment.duration for segment in playlist.segments])
    playlist.target_duration = max_segment_duration

    return playlist.dump('playlist.m3u8')


if __name__ == "__main__":
    main()
