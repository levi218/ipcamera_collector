from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
import sys
import os
import logging
logging.basicConfig(level=logging.DEBUG)
import datetime
import cv2
import collections
import logging
import platform
import threading
import time
from pathlib import Path
from queue import Queue
from typing import Callable, List

import av

from rtspbrute.modules import attack, utils, worker
from rtspbrute.modules.cli.input import parser
from rtspbrute.modules.cli.output import console, progress_bar
from rtspbrute.modules.rtsp import RTSPClient
from rtspbrute.modules.utils import parse_input_line


def start_threads(number: int, target: Callable, *args) -> List[threading.Thread]:
    threads = []
    for _ in range(number):
        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        threads.append(thread)
        thread.start()
    return threads


def wait_for(queue: Queue, threads: List[threading.Thread]):
    """Waits for queue and then threads to finish."""
    queue.join()
    [queue.put(None) for _ in range(len(threads))]
    [t.join() for t in threads]


def get_camera_ip():
    # Logging module set up
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # This disables ValueError from av module printing to console, but this also
    # means we won't get any logs from av, if they aren't FATAL or PANIC level.
    av.logging.set_level(av.logging.FATAL)

    # Progress output set up
    worker.PROGRESS_BAR = progress_bar

    # Targets, routes, credentials and ports set up
    targets = collections.deque(set([
            target for target in parse_input_line("192.168.1.0/24")
        ]))
    attack.ROUTES = ["/11", "/", "/H.264"]
    attack.CREDENTIALS = ["admin:admin", "user:user", "admin:VCKDUF"]
    attack.PORTS = ["554"]

    check_queue = Queue()
    brute_queue = Queue()
    screenshot_queue = Queue()

    if platform.system() == "Linux":
        import resource

        _, _max = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (_max, _max))
        console.print(f"[yellow]Temporary ulimit -n set to {_max}")

    logger.debug(f"Starting threads of worker.brute_routes")
    check_threads = start_threads(
        500, worker.brute_routes, check_queue, brute_queue
    )
    logger.debug(
            f"Starting threads of worker.brute_credentials"
        )
    brute_threads = start_threads(
        200, worker.brute_credentials, brute_queue, screenshot_queue
    )
    logger.debug(
            f"Starting threads of worker.screenshot_targets"
        )

    console.print("[green]Starting...\n")

    # progress_bar.update(worker.CHECK_PROGRESS, total=len(targets))
    # progress_bar.start()
    while targets:
        check_queue.put(RTSPClient(ip=targets.popleft(), timeout=2))

    wait_for(check_queue, check_threads)
    logger.debug("Check queue and threads finished")
    wait_for(brute_queue, brute_threads)
    return [client.ip for client in screenshot_queue.queue]


# get_camera_ip()
DIR_NAME = os.path.join(os.getcwd(), 'images') if os.environ.get("DIR_NAME", None) is None else os.environ.get("DIR_NAME", None)
STREAM_CREDENTIALS = os.environ.get("STREAM_CREDENTIALS", None)
STREAM_ROUTE = os.environ.get("STREAM_ROUTE", None)
if STREAM_CREDENTIALS is None or STREAM_ROUTE is None:
    raise Exception("STREAM URL MUST NOT BE EMPTY")

cap = None

def refresh_stream():
    global cap
    ips = get_camera_ip()
    if not ips:
        print("camera not found")
        return
    stream_url = "rtsp://" + STREAM_CREDENTIALS + "@" + ips[0] +":554"+ STREAM_ROUTE
    print("Fetching from "+stream_url)
    cap = cv2.VideoCapture(stream_url, apiPreference=cv2.CAP_FFMPEG)


def sensor():
    """ Function for test purposes. """
    global cap
    print("Scheduler is alive!", flush=True)
    current_hour = datetime.datetime.now().hour
    # if current_hour<int(os.environ.get("RECORD_FROM", 7)) or current_hour>int(os.environ.get("RECORD_TO", 19)):
    #     return
    filename = str(datetime.datetime.now().strftime('%Y%m%d-%H-%M-%S'))
    if cap is not None and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed")
        else:
            print("capturing frame")
            scale_percent = 70 # percent of original size
            width = int(frame.shape[1] * scale_percent / 100)
            height = int(frame.shape[0] * scale_percent / 100)
            dim = (width, height)
            
            # resize image
            resized = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)
            # cv2.imshow('frame', frame)
            #The received "frame" will be saved. Or you can manipulate "frame" as per your needs.
            name = str(filename)+".jpg"
            save_path = os.path.normpath(os.path.join(DIR_NAME,name))
            if not cv2.imwrite(save_path, resized):
                print("write image failed")
    else:
        cap = None
        print("no connection, refreshing!")
        refresh_stream()
        sensor()
    # cap.release()
    # cv2.destroyAllWindows()

app = Flask(__name__)

@app.route('/') 
def hello():
    return 'Hello World!'

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    sched = BackgroundScheduler()
    sched.add_job(sensor,'interval',seconds=int(os.environ.get("CAPTURE_INTERVAL", 2)))
    sched.start()

# if __name__ == "__main__": 
#     app.run()