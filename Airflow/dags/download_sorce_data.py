import pendulum
import os
import json
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
KAFKA_PORT = os.getenv('KAFKA_PORT')
KAFKA_TOPICS = {
    'browser_events.jsonl': os.getenv('BROWSER_EVENTS_TOPIC'),
    'device_events.jsonl': os.getenv('DEVICE_EVENTS_TOPIC'),
    'geo_events.jsonl': os.getenv('GEO_EVENTS_TOPIC'),
    'location_events.jsonl': os.getenv('LOCATION_EVENTS_TOPIC')
}


@dag(
    default_args=DEFAULT_ARGS,
    schedule_interval="2 * * * *",
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
            downloaded_files = fo.read().split('\n')

        # Получаем список файлов из хранилища
        session = boto3.Session(
            aws_access_key_id=Variable.get('ycloud_access_key_id'),
            aws_secret_access_key=Variable.get('ycloud_secret_access_key'),
            region_name="ru-central1",
        )

        s3 = session.client("s3", endpoint_url=ENDPOINT)

        new_files = []
        for key in s3.list_objects(Bucket='npl-de13-lab6-data')['Contents']:
            key = key['Key']
            if key not in downloaded_files:
                new_files.append(key)
        
        return new_files


    @task
    def send_to_kafka(files_to_download: List[str]):
        import requests
        import io
        from confluent_kafka import Producer
        import socket
        import zipfile

        conf = {
            'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
            'client.id': socket.gethostname(),
        }

        producer = Producer(conf)

        # Скачиваем файлы и отправляем в кафку
        skipped_files = []
        for key in files_to_download:
            filename, ext = os.path.splitext(key.split('/')[-1])
            if ext != '.zip':
                skipped_files.append(key)
                continue

            year, month, day, hour, _ = key.split('/')
            bucket_time = {'batch_time': f"{year[-4:]}-{month[-2:]}-{day[-2:]} {hour[-2:]}:00:00"}
            
            print(f'Скачиваем файл {key}')
            response = requests.get(URL + key)
            with zipfile.ZipFile(io.BytesIO(response.content)) as thezip:
                text = thezip.read(filename).decode('utf-8')
            
            topic = KAFKA_TOPICS[filename]
            print(f'Отправляем данные в топик {topic}')
            for line in text.split('\n'):
                try:
                     js = json.loads(line)
                except:
                    continue
                js.update(bucket_time)
                message = json.dumps(js).encode('utf-8')

                producer.produce(
                    topic,
                    key=f'{pendulum.now().timestamp()}',
                    value=message,
                )
            producer.flush()

            print(f'Записываем информацию об отправленном фале')
            with open(BUCKETS_FILE, 'a') as fo:
                fo.write(key + '\n')
            

        print('Все данные отправлены')


    @task
    def join_data():
        from clickhouse_driver import Client
        import time

        # Ждём 10 секунд, чтобы все данные точно долетели
        time.sleep(10)

        client = Client(host='185.130.113.27', port='19000', settings={'use_numpy': True})

        filt = f"batch_time > (SELECT MAX(batch_time) FROM {os.getenv('UNION_TABLE')})"
        browser_query = f"""
    SELECT *
    FROM {os.getenv('BROWSER_EVENTS_TABLE')}
    WHERE {filt}
        """
        device_query = f"""
    SELECT DISTINCT *
    FROM {os.getenv('DEVICE_EVENTS_TABLE')}
    WHERE {filt}
        """
        geo_query = f"""
    SELECT DISTINCT *
    FROM {os.getenv('GEO_EVENTS_TABLE')}
    WHERE {filt}
        """
        location_query = f"""
    SELECT *
    FROM {os.getenv('LOCATION_EVENTS_TABLE')}
    WHERE {filt}
        """

        query = f"""
SELECT 
    events.event_id AS event_id,
    events.event_timestamp AS event_timestamp,
    events.event_type AS event_type,
    events.click_id AS click_id,
    events.browser_name AS browser_name,
    events.browser_user_agent AS browser_user_agent,
    events.browser_language AS browser_language,
    events.batch_time AS batch_time,
    
    devices.os AS os,
    devices.os_name AS os_name,
    devices.os_timezone AS os_timezone,
    devices.device_type AS device_type,
    devices.device_is_mobile AS device_is_mobile,
    devices.user_custom_id AS user_custom_id,
    devices.user_domain_id AS user_domain_id,
    
    geo.geo_latitude AS geo_latitude,
    geo.geo_longitude AS geo_longitude,
    geo.geo_country AS geo_country,
    geo.geo_timezone AS geo_timezone,
    geo.geo_region_name AS geo_region_name,
    geo.ip_address AS ip_address,
    
    location.page_url AS page_url,
    location.page_url_path AS page_url_path,
    location.referer_url AS referer_url,
    location.referer_medium AS referer_medium,
    location.utm_medium AS utm_medium,
    location.utm_source AS utm_source,
    location.utm_content AS utm_content,
    location.utm_campaign AS utm_campaign
    
FROM ({browser_query}) events
LEFT JOIN ({device_query}) devices ON events.click_id=devices.click_id AND events.batch_time=devices.batch_time
LEFT JOIN ({geo_query}) geo ON events.click_id=geo.click_id AND events.batch_time=geo.batch_time
LEFT JOIN ({location_query}) location ON events.event_id=location.event_id AND events.batch_time=location.batch_time
"""
        insert_query = f"INSERT INTO {os.getenv('UNION_TABLE')} {query}"
        print(insert_query)

        client.execute(insert_query)


    send_to_kafka(check_buckets_file >> get_files_to_download()) >> join_data()


actual_dag = yandex_data_download()
