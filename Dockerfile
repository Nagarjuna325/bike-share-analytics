# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask>=3.1.2 \
    flask-sqlalchemy>=3.1.1 \
    psycopg2-binary>=2.9.10 \
    python-dotenv>=1.1.1 \
    groq>=0.31.0 \
    sentence-transformers \
    numpy>=2.3.2 \
    gunicorn>=23.0.0 \
    email-validator>=2.3.0

# Expose port 5000
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]