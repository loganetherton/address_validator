FROM python:3.10.0

RUN apt-get update && apt-get -y install coreutils
# RUN mknod /dev/null c 1 3

WORKDIR /app

COPY requirements.txt .
COPY app.py .
COPY cache.py .
COPY config.py .
COPY test_app.py .
COPY pytest_setup.ini .
COPY csv /app/csv
COPY test_csv /app/test_csv

# Maybe put this in a venv
RUN pip install -r requirements.txt
# Make sure all tests pass
RUN pytest -c /app/pytest_setup.ini
# Go ahead and run based on the CSV dir
CMD python app.py
