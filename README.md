# newprolab-project
Final project for NewProLab DE course

## Запуск докеров

1. Перед запуском нужно раздать права на директории

Постгрес особенный, он не переваривает непустые директории

```bash
mkdir data/postgres_data/db
```

Кафка особенная, ей почему-то нужны расширенные права на директорию

```bash
sudo chown -R 1001:1001 data/kafka_data
```

2. Затем запускаем сами сервисы

Если уже были попытки запустить сервисы из других директорий, то лучше поудалять собранные ранее контейнеры с томами:

```bash
docker container remove airflow-scheduler
docker container remove airflow-webserver
docker container remove airflow-initdb
docker container remove clickhouse-server
docker container remove postgres
docker container remove kafka
docker volume rm newprolab-project_kafka_data
docker volume rm newprolab-project_clickhouse_db
docker volume rm newprolab-project_airflow_postgres_db
docker volume rm newprolab-project_airflow_dags
```

Сам запуск докеров

```bash
docker-compose -f docker-compose.yml up
```

3. После того, как убедились, что всё работает, гасим и переподнимаем в фоновом режиме

```bash
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml up -d
```

**!!!ПОСЛЕ ПЕРВОГО ЗАПУСКА ИЗ docker-compose НУЖНО УДАЛИТЬ ДОКЕР init_db**

В противном случае база airflow будет перезатираться при каждом запуске.

4. Теперь нужно создать пользователя в Airflow:

**!!!** По дефолту создаётся пользователь airflow-airflow, но это несекьюрно, поэтому его надо удалить и создать нового.

Заходим на webserver
```bash
$ docker-compose exec airflow-webserver bash
```
Создаём админа
```bash
airflow users create -u admin -f Ad -l Min -r Admin -e admin@adm.in
```

5. Создаём в клике нужные таблицы

```bash
python ./Clickhouse/create_tables.py
```

6. Записываем пробные данные (опционально)

```bash
cat ./data/sample/browser_events.jsonl | clickhouse-client --port 19000 --multiline --query="INSERT into browser_events format JSONEachRow"
cat ./data/sample/device_events.jsonl | clickhouse-client --port 19000 --multiline --query="INSERT into device_events format JSONEachRow"
cat ./data/sample/geo_events.jsonl | clickhouse-client --port 19000 --multiline --query="INSERT into geo_events format JSONEachRow"
cat ./data/sample/location_events.jsonl | clickhouse-client --port 19000 --multiline --query="INSERT into location_events format JSONEachRow"
```

