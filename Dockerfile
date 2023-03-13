# syntax=docker/dockerfile:1.3
FROM python:3.11-bullseye

WORKDIR /

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY ../ .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

