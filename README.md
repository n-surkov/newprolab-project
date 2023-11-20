# newprolab-project
Final project for NewProLab DE course

## Запуск докеров

1. Перед запуском нужно раздать права на директории

```bash
sudo chown -R 1001:1001 data/kafka_data
sudo chown -R 1001:1001 data/clickhouse/db
sudo chown -R 1001:1001 data/postgres_data
```

2. Затем запускаем сами сервисы

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