FROM python:3.9-alpine

COPY deemon /app/deemon

COPY deemon-docker.sh /app/script.sh

COPY requirements.txt /app

RUN \
echo "*** Building container ***" && \
apk add shadow gcc python3-dev build-base jq py3-pip python3 && \
pip install -r /app/requirements.txt && \
mkdir -p /app/Music && \
ln -sf /app/.config/deemon /config && \
ln -sf /music /app/Music/deemix\ Music && \
ln -sf /app/.config/deemix /deemix

ENV PYTHONPATH "${PYTHONPATH}:/app"

RUN useradd --home-dir /app -s /bin/sh deemon
RUN chown deemon:deemon /app

CMD ["/bin/ash", "/app/script.sh"]

VOLUME /config /music /deemix
