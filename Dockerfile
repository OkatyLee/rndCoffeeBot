FROM python:3.9-slim


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
#RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY af /app

WORKDIR /app
