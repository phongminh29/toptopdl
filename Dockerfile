FROM python:3.9-slim
WORKDIR /code
RUN apt-get update && apt-get install -y ffmpeg
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Render sẽ cấp một cổng ngẫu nhiên qua biến PORT
CMD ["python", "main.py"]