
FROM python:latest

WORKDIR /app

COPY ./requirements.txt /app

RUN pip install --upgrade pip && pip install -r requirements.txt --no-cache-dir

COPY . /app

