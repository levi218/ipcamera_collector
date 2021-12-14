from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
import sys
import os
import logging
logging.basicConfig(level=logging.DEBUG)
import datetime
import cv2

DIR_NAME = os.path.join(os.getcwd(), 'images') if os.environ.get("DIR_NAME", None) is None else os.environ.get("DIR_NAME", None)
STREAM_URL = os.environ.get("STREAM_URL", None)
if STREAM_URL is None:
    raise Exception("STREAM URL MUST NOT BE EMPTY")
# cap = cv2.VideoCapture(STREAM_URL)

def sensor():
    """ Function for test purposes. """
    print("Scheduler is alive!", flush=True)
    print("Fetching from "+STREAM_URL)
    cap = cv2.VideoCapture(STREAM_URL)
    current_hour = datetime.datetime.now().hour
    # if current_hour<int(os.environ.get("RECORD_FROM", 7)) or current_hour>int(os.environ.get("RECORD_TO", 19)):
    #     return
    filename = str(datetime.datetime.now().strftime('%Y%m%d-%H-%M-%S'))
    if cap.isOpened():
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
        print("connection failed!")
    cap.release()
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