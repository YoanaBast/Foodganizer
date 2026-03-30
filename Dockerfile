FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies first (cached layer, faster rebuilds)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# manually ensure errors folder is in staticfiles, collectstatic is in the yml
RUN mkdir -p /app/staticfiles/errors && \
    cp /app/static/errors/413.html /app/staticfiles/errors/413.html