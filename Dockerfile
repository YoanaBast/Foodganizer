FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/staticfiles/errors && \
    cp /app/static/errors/413.html /app/staticfiles/errors/413.html

RUN sed -i 's/\r$//' start.sh && chmod +x start.sh
