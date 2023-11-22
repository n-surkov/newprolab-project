import pendulum
import os
from typing import List
from airflow.models import Variable
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.operators.dummy import DummyOperator
from airflow.operators.bash import BashOperator


DEFAULT_ARGS = {"owner": "beautiful-team"}
BUCKETS_FILE = '/app/share/downloaded_buckets.txt'

# Параметры хранилища
STORAGE = "storage.yandexcloud.net"
BUCKET = 'npl-de13-lab6-data'
ENDPOINT = "https://" + STORAGE
URL = "https://" + BUCKET + '.' + STORAGE + '/'

# Маппинг файлов с топиками
KAFKA_HOST = os.getenv('KAFKA_HOST')
topics = {
    'browser_events.jsonl.zip': os.getenv('BROWSER_EVENTS_TOPIC'),
    'device_events.jsonl.zip': os.getenv('DEVICE_EVENTS_TOPIC'),
    'geo_events.jsonl.zip': os.getenv('GEO_EVENTS_TOPIC'),
    'location_events.jsonl.zip': os.getenv('LOCATION_EVENTS_TOPIC')
}


@dag(
    default_args=DEFAULT_ARGS,
    schedule_interval="0 * * * *",
    start_date=pendulum.datetime(2020, 11, 22),
    catchup=False,
)
def yandex_data_download():
    check_buckets_file = BashOperator(
        task_id='check_buckets_file',
        bash_command=f"touch {BUCKETS_FILE}",
    )
    
    @task
    def get_files_to_download():
        import boto3

        # Загружаем список уже обработанных файлов
        with open(BUCKETS_FILE, 'r') as fo:
            downloaded_files = list(fo.readlines())

        # Получаем список файлов из хранилища
        session = boto3.Session(
            aws_access_key_id=Variable.get('ycloud_access_key_id'),
            aws_secret_access_key=Variable.get('ycloud_secret_access_key'),
            region_name="ru-central1",
        )

        s3 = session.client("s3", endpoint_url=ENDPOINT)

        new_files = []
        for key in s3.list_objects(Bucket='npl-de13-lab6-data')['Contents']:
            if key not in downloaded_files:
                new_files.append(key)
        
        return new_files


    @task
    def send_to_kafka(files_to_download: List[str]):
        import requests
        import io
        from confluent_kafka import Producer
        import socket
        import datetime

        print(files_to_download)


    send_to_kafka(check_buckets_file >> get_files_to_download())


actual_dag = yandex_data_download()