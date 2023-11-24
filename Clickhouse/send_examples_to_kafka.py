"""
Скрипт отправки тестовых данных в Кафку
"""
import os

from confluent_kafka import Producer
import socket
import datetime
from read_config import parse_parameters

DATA_SAMPLE_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample')
CURRENT_TIME = datetime.datetime.now().strftime('%Y-%m-%d %H:00:00')

TOPICS = {
    'browser_events.jsonl': 'BROWSER_EVENTS_TOPIC',
    'device_events.jsonl': 'DEVICE_EVENTS_TOPIC',
    'geo_events.jsonl': 'GEO_EVENTS_TOPIC',
    'location_events.jsonl': 'LOCATION_EVENTS_TOPIC',
}

def send_sample(producer, topic, filename):
    filepath = os.path.join(DATA_SAMPLE_FOLDER, filename)

    with open(filepath, 'r') as fo:
        for line in fo.readlines():
            data = line.strip()
            data = data[:-1] + f', "batch_time": "{CURRENT_TIME}"}}'
            producer.produce(
                topic,
                key=f'{datetime.datetime.now().timestamp()}',
                value=data,
            )


if __name__ == '__main__':
    config = parse_parameters()

    print(f"Данные будут записываться в кафку {config['KAFKA_HOST']}:{config['KAFKA_PORT']} в следующие топики:")

    for key, val in TOPICS.items():
        print(f"* {key} в топик {config[val]}")

    conf = {
        'bootstrap.servers': f"{config['KAFKA_HOST']}:{config['KAFKA_PORT']}",
        'client.id': socket.gethostname(),
    }

    producer = Producer(conf)
    
    for file, topic_key in TOPICS.items():
        print(config[topic_key], file)
        send_sample(producer, config[topic_key], file)
        producer.flush()
