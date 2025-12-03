FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Ставимо системні бібліотеки для Postgres
RUN apt-get update && apt-get install -y libpq-dev gcc

# Ставимо Python бібліотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо проєкт
COPY . .

# Збираємо статику (щоб CSS працював через Gunicorn)
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Запуск сайту за замовчуванням
CMD ["gunicorn", "core.asgi:application", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "--workers", "3"]