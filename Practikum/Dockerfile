FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/static/codemirror/lib && cp /app/static/codemirror/src/codemirror.js /app/static/codemirror/lib/codemirror.js && cp /app/static/codemirror/src/codemirror.css /app/static/codemirror/lib/codemirror.css

EXPOSE 8000

CMD ["gunicorn", "Practikum.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
