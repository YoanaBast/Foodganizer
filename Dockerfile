FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies first (cached layer, faster rebuilds)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Collect static files into the staticfiles/ folder
RUN python manage.py collectstatic --noinput