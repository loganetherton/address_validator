FROM python:3.10.0-slim

WORKDIR /app
COPY requirements.txt .
COPY app.py .
COPY test_app.py .
COPY config.py .
COPY test_input_bad_header.csv .

RUN python -m venv venv

RUN /app/venv/bin/pip install -r requirements.txt

CMD ['/app/venv/bin/python', 'pytest']
