import os
PROJECT_PATH = os.path.join(os.path.dirname(__file__))
DOCKER_COMPOSE_PATH = os.path.join(PROJECT_PATH, 'docker-compose.yml')
ENV_PATH = os.path.join(PROJECT_PATH, 'env.conf')
AIRFLOW_ENV_PATH = os.path.join(PROJECT_PATH, 'Airflow', 'airflow-variables.env')

def parse_parameters(filename=ENV_PATH):
    config = dict()
    with open(filename, 'r') as fo:
        for line in fo.readlines():
            comment_start = line.find('#')
            if comment_start == -1:
                line = line.strip()
            else:
                line = line[:comment_start].strip()
            if line != '':
                key, val = line.split('=')
                config[key] = val
    
    if config['USE_EXTERNAL_KAFKA'] == 'NO':
        config['KAFKA_HOST'] = config['HOST']
    if config['USE_EXTERNAL_CLICKHOUSE'] == 'NO':
        config['CLICKHOUSE_HOST'] = config['HOST']
    return config

if __name__=="__main__":
    # Парсим параметры
    config = parse_parameters()
    print(config)

    # Собираем docker-compose.yml
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
      - ./Clickhouse/config.xml:/etc/clickhouse-server/config.xml
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
    
    airflow_service = f"""
  postgres:
    image: "postgres:14.2"
    container_name: "postgres"
    environment:
      - POSTGRES_USER=airflow
      - POSTGRES_PASSWORD=airflow
      - POSTGRES_DB=airflow
    ports:
      - "5432:5432"
    volumes:
      - airflow_postgres_db:/var/lib/postgresql/data

  # удали/закомментируй меня после первого запуска
  # так же удали зависимости следующих 2 сервисов от меня
  airflow-initdb:
    image: "docker5300/marmot-hole"
    container_name: airflow-initdb
    depends_on:
      - postgres
    volumes:
      - ./Airflow/airflow.cfg:/usr/local/airflow/airflow.cfg
    entrypoint: /bin/bash
    command:
      - -c
      - airflow users list || ( airflow db init &&
        airflow users create
          --role Admin
          --username airflow
          --password airflow
          --email airflow@airflow.com
          --firstname airflow
          --lastname airflow )
    restart: on-failure

  airflow-webserver:
    image: "docker5300/marmot-hole"
    container_name: airflow-webserver
    restart: always
    depends_on:
      - postgres
      - airflow-initdb
    volumes:
      - airflow_dags:/usr/local/airflow/dags
      - ./Airflow/airflow.cfg:/usr/local/airflow/airflow.cfg
      - share_drive:/app/share
    ports:
      - "{config['AIRFLOW_WEBSERVER_PORT']}:8080"
    env_file:
      - Airflow/airflow-variables.env
    entrypoint: airflow webserver

  airflow-scheduler:
    image: "docker5300/marmot-hole"
    container_name: airflow-scheduler
    restart: always
    depends_on:
      - postgres
      - airflow-initdb
    volumes:
      - ./Airflow/airflow.cfg:/usr/local/airflow/airflow.cfg
      - airflow_dags:/usr/local/airflow/dags
      - share_drive:/app/share
    env_file:
      - Airflow/airflow-variables.env
    entrypoint: airflow scheduler
""".strip()
    
    airflow_volumes = f"""
  airflow_postgres_db:
    driver: local
    driver_opts:
      type: none
      device: {config['AIRFLOW_DATABASE']}
      o: bind
  airflow_dags:
    driver: local
    driver_opts:
      type: none
      device: {config['AIRFLOW_DAGS']}
      o: bind
  share_drive:
    driver: local
    driver_opts:
      type: none
      device: {config['AIRFLOW_SHARE']}
      o: bind
""".strip()

    docker_compose = f"""
version: "3"

services:
  {kafka_service if config['USE_EXTERNAL_KAFKA'] == 'NO' else ''}
  {clickhouse_service if config['USE_EXTERNAL_CLICKHOUSE'] == 'NO' else ''}
  {airflow_service if config['USE_EXTERNAL_AIRFLOW'] == 'NO' else ''}

volumes:
  {kafka_volumes if config['USE_EXTERNAL_KAFKA'] == 'NO' else ''}
  {clickhouse_volumes if config['USE_EXTERNAL_CLICKHOUSE'] == 'NO' else ''}
  {airflow_volumes if config['USE_EXTERNAL_AIRFLOW'] == 'NO' else ''}
"""
    
    with open(DOCKER_COMPOSE_PATH, 'w') as fo:
        fo.write(docker_compose)

    # Обновляем параметры среды Airflow
    envireonment = ''
    for key, val in config.items():
        envireonment += f'{key}={val}\n'

    with open(AIRFLOW_ENV_PATH, 'w') as fo:
        fo.write(envireonment)
