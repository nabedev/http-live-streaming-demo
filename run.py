import time
import uuid

import cv2
import m3u8
from m3u8.model import Segment
import ffmpeg
import ffmpy


DEVICE_ID = 0
FPS = 10
CODECS = 'XVID'
CAPTURE_DURATION = 10


def main():
    vc = cv2.VideoCapture(DEVICE_ID)
    width = int(vc.get(3))
    height = int(vc.get(4))

    video_filepath = 'video/{}.avi'.format(uuid.uuid4())
    fourcc = cv2.VideoWriter_fourcc(*CODECS)
    writer = cv2.VideoWriter(video_filepath, fourcc, FPS, (width, height))

    start_time = time.time()
    while(vc.isOpened()):
        if time.time() - start_time > CAPTURE_DURATION:
            segment = generate_segment(video_filepath)
            update_playlist(segment)

            video_filepath = 'video/{}.avi'.format(uuid.uuid4())
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
    segment_filepath = 'output/{}.ts'.format(uuid.uuid4())

    ff = ffmpy.FFmpeg(
        inputs={filepath: None},
        outputs={segment_filepath: None},
    )
    ff.run()

    return Segment(
        uri=segment_filepath,
        base_uri='',
        duration=CAPTURE_DURATION,
    )


def update_playlist(segment):
    playlist = m3u8.load('playlist.m3u8')
    playlist.segments.append(segment)

    # Keep up to 3 segment files
    # https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/StreamingMediaGuide/FrequentlyAskedQuestions/FrequentlyAskedQuestions.html#//apple_ref/doc/uid/TP40008332-CH103-SW1
    if (len(playlist.segments) > 3):
        playlist.segments.pop(0)

    return playlist.dump('playlist.m3u8')


if __name__ == "__main__":
    main()
