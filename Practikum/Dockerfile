FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Собираем статику
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "Practikum.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
