FROM python:3.8.13

RUN pip install --user psycopg2-binary==2.9.3\
 apache-airflow==2.3.0\ 
 pandas numpy clickhouse-driver redis

WORKDIR /usr/local/airflow
ENV AIRFLOW_HOME=/usr/local/airflow
ENV PATH=/root/.local/bin:$PATH