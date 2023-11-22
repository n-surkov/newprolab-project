FROM python:3.8.13

COPY requirements.txt /app

RUN pip install --user -r /app/requirements.txt

WORKDIR /usr/local/airflow
ENV AIRFLOW_HOME=/usr/local/airflow
ENV PATH=/root/.local/bin:$PATH