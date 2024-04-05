FROM ubuntu:22.04

RUN apt-get update -y && \
apt-get install -y python3-pip

COPY ./requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt && \
mkdir /config && mkdir /deemix && mkdir /downloads && mkdir /import && \
mkdir /root/.config && \
ln -s /config /root/.config/deemon && \
ln -s /deemix /root/.config/deemix

COPY deemon /app/deemon

ENV PYTHONPATH="$PYTHONPATH:/app"

VOLUME /config /downloads /import /deemix
