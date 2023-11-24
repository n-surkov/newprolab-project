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
        
        return new_files[:100]


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
            bucket_time = f"{year[-4:]}-{month[-2:]}-{day[-2:]} {hour[-2:]}:00:00"
            
            print(f'Скачиваем файл {key}')
            response = requests.get(URL + key)
            with zipfile.ZipFile(io.BytesIO(response.content)) as thezip:
                text = thezip.read(filename).decode('utf-8')
            
            topic = KAFKA_TOPICS[filename]
            print(f'Отправляем данные в топик {topic}')
            for line in text.split('\n'):
                if not line:
                    continue
                data = line[:-1] + f',"batch_time":"{bucket_time}"}}'
                producer.produce(
                    topic,
                    key=f'{pendulum.now().timestamp()}',
                    value=data,
                )
            producer.flush()

            print(f'Записываем информацию об отправленном фале')
            with open(BUCKETS_FILE, 'a') as fo:
                fo.write(key + '\n')
            

        print('Все данные отправлены')


    send_to_kafka(check_buckets_file >> get_files_to_download())


actual_dag = yandex_data_download()
