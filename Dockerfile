# ----------- Build Stage -------------
    FROM python:3.10-slim AS builder

    WORKDIR /app
    
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        libffi-dev \
        && rm -rf /var/lib/apt/lists/*
    
    COPY requirements.txt .
    RUN pip install --upgrade pip 
    RUN pip install --prefix=/install --no-cache-dir -r requirements.txt
    
    # ----------- Runtime Stage ------------
    FROM python:3.10-slim
    
    WORKDIR /app
    
    RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        libffi-dev \
        && rm -rf /var/lib/apt/lists/*
    
    COPY --from=builder /install /usr/local
    COPY . .
    
    ENV PYTHONUNBUFFERED=1
    ENV DJANGO_SETTINGS_MODULE=credify.settings
    
    CMD ["gunicorn", "--bind", "0.0.0.0:8000", "credify.wsgi:application"]
    