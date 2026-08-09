FROM python:3.11-slim

WORKDIR /app

# Text-only build: no ffmpeg needed. When enabling the audio/OpenMHz path,
# add:  RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

CMD ["python", "worker.py"]
