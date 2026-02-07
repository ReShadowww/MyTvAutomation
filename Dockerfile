FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .              # Copy requirements
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                             # Copy your Flask app+templates
EXPOSE 5000
CMD ["python", "app.py"]