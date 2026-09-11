FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBUG=0
WORKDIR /app

# Install dependencies first, so code changes don't invalidate this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# collectstatic needs settings but no real secrets or database.
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home studio && mkdir -p /app/media && chown studio /app/media
USER studio

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
