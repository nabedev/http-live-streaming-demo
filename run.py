import time
import uuid
from pathlib import Path

import cv2
import m3u8
import ffmpeg


DEVICE_ID = 0
FPS = 10
CODECS = 'mp4v'
CAPTURE_DURATION = 10


def main():
    vc = cv2.VideoCapture(DEVICE_ID)
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
        m3u8.model.Segment object
    """
    filename = Path(filepath).name
    segment_filepath = f'output/{filename}'

    # HACK: videoはCAPTURE_DURATIONおきに書き出すが、
    # 生成されるセグメントファイルは1つとは限らない(?)
    # 複数作成される場合に対応する必要がある。
    # どこかのタイミングで不要になった.mp4 .ts .m3u8ファイルを削除する必要がある。
    input_stream = ffmpeg.input(filepath, format='mp4')
    output_stream = ffmpeg.output(
        stream=input_stream,
        filename=f'{segment_filepath}.m3u8',
        format='hls',
        hls_time=CAPTURE_DURATION,
        hls_list_size=3,
    )
    ffmpeg.run(output_stream)

    playlist = m3u8.load(f'{segment_filepath}.m3u8')
    return playlist.segments[0]


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
