FROM borda/docker_python-opencv-ffmpeg:cpu-py3.9-cv4.5.4

WORKDIR /
RUN apt update
RUN apt -y install build-essential libwrap0-dev libssl-dev libc-ares-dev uuid-dev xsltproc
RUN apt-get update -qq \
    && apt-get install --no-install-recommends --yes \
        build-essential \
        gcc \
        python3-dev \
        mosquitto \
        mosquitto-clients 

RUN python3 -c "import cv2; print(cv2.__version__)"
RUN pip3 install --upgrade pip setuptools wheel

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
EXPOSE 5000
COPY . .
# RUN cat .env
# RUN ls
WORKDIR /src

CMD ["flask", "run"]