import os

from confluent_kafka import Producer
import socket
import datetime

KAFKA_HOST = '146.185.242.74'
KAFKA_PORT = '19092'

DATA_SAMPLE_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sample', )

def send_sample(producer, topic, filename):
    filepath = os.path.join(DATA_SAMPLE_FOLDER, filename)
    with open(filepath, 'r') as fo:
        for line in fo.readlines():
            producer.produce(
                topic,
                key=f'{datetime.datetime.now().timestamp()}',
                value=line,
            )


if __name__ == '__main__':
    conf = {
        'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
        'client.id': socket.gethostname(),
    }

    producer = Producer(conf)
    
    send_sample(producer, 'browser_events_in', 'browser_events.jsonl')
    send_sample(producer, 'device_events_in', 'device_events.jsonl')
    send_sample(producer, 'geo_events_in', 'geo_events.jsonl')
    send_sample(producer, 'location_events_in', 'location_events.jsonl')
    
    producer.flush()