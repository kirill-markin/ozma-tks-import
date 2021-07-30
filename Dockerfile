FROM ubuntu:latest

RUN apt-get update \
# Python3
    && apt-get install -y python3-pip python3-dev \
    && cd /usr/local/bin \
    && ln -s /usr/bin/python3 python \
    && python -m pip install --upgrade pip

COPY /app /home/app
COPY ./requirements.txt /home/app
WORKDIR /home/app
RUN pip3 install -r ./requirements.txt

CMD python3 main.py
