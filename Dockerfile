
FROM python:3.13-slim

WORKDIR /app

COPY ./requirements.txt /app

RUN pip install --upgrade pip && pip install -r requirements.txt --no-cache-dir

COPY . /app

