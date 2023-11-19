import os

if __name__=="__main__":
    config = dict()
    with open('./env.conf', 'r') as fo:
        for line in fo.readlines():
            key, val = line.strip().split('=')
            config[key] = val
    
    print(config)

    kafka_service = f"""
  kafka:
    image: docker.io/bitnami/kafka:3.6
    container_name: kafka
    ports:
      - "{config['KAFKA_PORT']}:{config['KAFKA_PORT']}"
    volumes:
      - kafka_data:/bitnami
    environment:
      # KRaft settings
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka:9093
      # Listeners
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093,CONNECTIONS_FROM_HOST://0.0.0.0:19092
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://:9092,CONNECTIONS_FROM_HOST://{config['HOST']}:19092
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,CONNECTIONS_FROM_HOST:PLAINTEXT
      - KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=PLAINTEXT
""".strip()
    kafka_volumes = f"""
  kafka_data:
    driver: local
    driver_opts:
      type: none
      device: {config['KAFKA_DATA']}
      o: bind
""".strip()
    
    clickhouse_service = f"""
  clickhouse-server:
    image: yandex/clickhouse-server
    container_name: clickhouse-server
    ports:
      - '{config['CLICKHOUSE_OUT_PORT']}:8123'
      - '{config['CLICKHOUSE_CLIENT_PORT']}:9000'
    volumes:
      - clickhouse_db:/var/lib/clickhouse
      - ./data/clickhouse/config.xml:/etc/clickhouse-server/config.xml
    ulimits:
      nofile: 262144
""".strip()
    
    clickhouse_volumes = f"""
  clickhouse_db:
    driver: local
    driver_opts:
      type: none
      device: {config['CLICKHOUSE_DATA']}
      o: bind
""".strip()

    docker_compose = f"""
version: "3"

services:
  {kafka_service if config['USE_EXTERNAL_KAFKA'] == 'NO' else ''}
  {clickhouse_service if config['USE_EXTERNAL_CLICKHOUSE'] == 'NO' else ''}

volumes:
  {kafka_volumes if config['USE_EXTERNAL_KAFKA'] == 'NO' else ''}
  {clickhouse_volumes if config['USE_EXTERNAL_CLICKHOUSE'] == 'NO' else ''}
"""
    
    with open('./docker-compose.yml', 'w') as fo:
        fo.write(docker_compose)
