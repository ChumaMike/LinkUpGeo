FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (layer cached until requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create uploads directory
RUN mkdir -p src/static/uploads

EXPOSE 5000

# Entrypoint: run migrations then start gunicorn
CMD ["sh", "-c", "flask db upgrade && gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 'src:create_app()'"]
