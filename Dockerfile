FROM python:3.8.12-slim-bullseye

RUN apt-get update && \
   apt-get install -y --no-install-recommends \
       liblapack-dev libatlas-base-dev && \
   rm -rf /var/lib/apt/lists/*

WORKDIR /srv/mkt2tour

COPY setup.py requirements.txt README.md /srv/mkt2tour/

RUN pip install --upgrade pip && \
    pip install --upgrade setuptools && \
    pip install --no-cache-dir -r /srv/mkt2tour/requirements.txt

COPY src /srv/mkt2tour/src
RUN pip install --no-cache-dir /srv/mkt2tour/

WORKDIR /
ENTRYPOINT [ "mkt2tour", "-vv" ]
