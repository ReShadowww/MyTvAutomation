FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .         # Copy requirements.txt into /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . .                        # Copy everything else (app.py and templates folder)

EXPOSE 5000

CMD ["python", "app.py"]