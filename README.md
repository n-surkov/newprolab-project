# newprolab-project

Финальный проект, суть которого заключается в том, что на основе данных, 
находящихся в хранилище S3 YandexCloud построить дашборды.

Для реализации этой задачи была выбрана следующая архитектура:

* Kafka на ноде 2 -- для приёма исходных джисонов
* Clickhouse на ноде 2 -- для хранения данных. Для каждого типа 
  данных реализована следующая схема, которую можно собрать с помощью 
  скрипта [create_tables](./Clickhouse/create_tables.py):
  * table_in -- таблица подключения к топику kafka
  * table -- таблица в которой будут храниться данные
  * table_mv -- вьюха, которая переливает данные из table_in в table
* Airflow на ноде 1 -- аркестрация процессов по переливке данных:
  * [Даг переливки данных](./Airflow/dags/download_sorce_data.py) -- 
  Осуществляет ежечасную выгрузку данных из хранилища S3 в соответствующие 
    топики Kafka
* Superset на ноде 3 -- отрисовка дашбордов.
    
Разделить Airflow и данные было решено потому, что кликхаус очень любит кушать 
память, а выгрузка данных их S3 в Kafka осуществляется так же с использованием 
оперативки. По этой же причине Superset вынесен на отдельную машину.

Данный проект позволяет поднять сервисы для обработки данных. 
Иными словами готовит почву, на которой Superset уже может рисовать дашборды.

<details>
<summary>Информация об исходных данных</summary>
В проекте содержится [маленький срез данных](./data/sample) для ознакомления:

* [browser_events.jsonl](./data/sample/browser_events.jsonl) &mdash; данные с информацией о просмотрах браузера
* [device_events.jsonl](./data/sample/device_events.jsonl) &mdash; данные об устройствах, с которых пользователи пользовались
  сайтом
* [geo_events.jsonl](./data/sample/geo_events.jsonl) &mdash; данные о локации пользователя
* [location_events.jsonl](./data/sample/location_events.jsonl) &mdash; вопреки названию, это данные не о локации
  пользователя, а непосредственно о положении пользователя на сайте и информации о том, откуда пользователь попал на
  страницу
  
### Браузер и идентификаторы события

Здесь приходит timestamp (UTC), тип события, и два уникальных поля `event_id` и `click_id`, которые используются для
склеивания с другими данными. Пример записи:

```json
{
  "event_id": "8cca1c7d-b0cc-4738-be92-c644101e3fff",
  "event_timestamp": "2022-11-28 20:51:05.627882",
  "event_type": "pageview",
  "click_id": "811320f1-3bc2-42b9-a841-5a1e5a812f2d",
  "browser_name": "Chrome",
  "browser_user_agent": "Mozilla/5.0 (Linux; Android 2.3.5) AppleWebKit/531.2 (KHTML, like Gecko) Chrome/32.0.833.0 Safari/531.2",
  "browser_language": "sat_IN"
}
```

### Информация об устройстве

Отсюда можно собрать данные об операционной системе и типе устройства. Склеить их с остальными данными можно по
полю `click_id`. Также в этих данных есть информация о пользователе. Пример записи (судя по операционной системе перед
нами путешественник из прошлого):

```json
{
  "click_id": "811320f1-3bc2-42b9-a841-5a1e5a812f2d",
  "os": "iPad; CPU iPad OS 4_2_1 like Mac OS X",
  "os_name": "iOS",
  "os_timezone": "Europe/Berlin",
  "device_type": "Mobile",
  "device_is_mobile": true,
  "user_custom_id": "aperry@yahoo.com",
  "user_domain_id": "1ab06c9f-0e2e-4f46-9b6c-91a0e9a86a4d"
}
```

### Данные о геопозиции

Вам известно, что тут вам в базовом наборе дали только неточные данные, которые уже все события привязывают к
определённому городу. Склеивать с остальными наборами данных нужно по полю `click_id`. Пример записи:

```json
{
  "click_id": "811320f1-3bc2-42b9-a841-5a1e5a812f2d",
  "geo_latitude": "50.82709",
  "geo_longitude": "6.9747",
  "geo_country": "DE",
  "geo_timezone": "Europe/Berlin",
  "geo_region_name": "Wesseling",
  "ip_address": "206.227.30.186"
}
```

### Информация о нахождении на сайте и откуда пользователь пришёл

В примере, который вам дали, явно фейковые данные, которые не соответствуют настоящему сайту, но поставщик данных
уверяет, что схема данных в реальной системе такая же. Склеивать с остальными данными можно по полю `event_id`. Помимо
непосредственно событий непосредственно посещения сайта, тут также маркетинговые метки. Пример записи:

```json
{
  "event_id": "8cca1c7d-b0cc-4738-be92-c644101e3fff",
  "page_url": "http://www.dummywebsite.com/home",
  "page_url_path": "/home",
  "referer_url": "www.facebook.com",
  "referer_medium": "internal",
  "utm_medium": "organic",
  "utm_source": "facebook",
  "utm_content": "ad_4",
  "utm_campaign": "campaign_2"
}
```
</details>

## Запуск докеров

### 1. Настройка конфигурационного файла

Данный проект позволяет как поднять все сервисы на 1 машине, 
так и разделить их между собой.
Все настройки осуществляются посредствам 
[конфигурационного файла](./env.conf):
* `HOST`: 
  адрес машины, на которой запускаются сервисы
* `USE_EXTERNAL_KAFKA`: 
  YES -- использовать предустановленную кафку. 
  NO -- поднять кафку в докере
* `KAFKA_HOST`: адрес поднятой кафки в случае `USE_EXTERNAL_KAFKA=YES`.
  В случае `USE_EXTERNAL_KAFKA=NO`, он будет равен `HOST`.
* `KAFKA_PORT`: порт, на котором поднята кафка 
  или на котором она будет поднята в контейнере
* `USE_EXTERNAL_CLICKHOUSE`: 
  YES -- использовать предустановленный кликхаус. 
  NO -- поднять кликхаус в докере
* `CLICKHOUSE_HOST`: адрес поднятого клика в случае 
  `USE_EXTERNAL_CLICKHOUSE=YES`.
  В случае `USE_EXTERNAL_CLICKHOUSE=NO`, он будет равен `HOST`.
* `CLICKHOUSE_CLIENT_PORT`: порт, на котором поднят клик 
  или на котором он будет поднят в контейнере
* `CLICKHOUSE_OUT_PORT`: порт, на котором поднят клик 
  или на котором он будет поднят в контейнере
* `KAFKA_DATA`: путь к директории, к которой будет примонтирована БД кафки.
* `CLICKHOUSE_DATA`: путь к директории, к которой будет примонтирована БД клика.
* `USE_EXTERNAL_AIRFLOW`: -- проверить используемость и удалить.
* `AIRFLOW_WEBSERVER_PORT`: порт, на котором будет поднят webserver Airflow.
* `AIRFLOW_DATABASE`: путь к директории, к которой будет примонтирована БД airflow.
* `AIRFLOW_DAGS`: путь к дагам airflow, которые будут передаваться в его контейнер.
* `AIRFLOW_SHARE`: путь к директории, к которой будет примонтирован tmp том airflow.
* `BROWSER_EVENTS_TABLE`: название таблицы для данных browser_events.
* `BROWSER_EVENTS_TOPIC`: название топика кафки для данных browser_events.
* `DEVICE_EVENTS_TABLE`: название таблицы для данных device_events.
* `DEVICE_EVENTS_TOPIC`: название топика кафки для данных device_events.
* `GEO_EVENTS_TABLE`: название таблицы для данных geo_events.
* `GEO_EVENTS_TOPIC`: название топика кафки для данных geo_events.
* `LOCATION_EVENTS_TABLE`: название таблицы для данных location_events.
* `LOCATION_EVENTS_TOPIC`: название топика кафки для данных location_events.


## Запуск докеров

0. Настраиваем конфигурацию

* правим конфигурационный файл [env.conf](./env.conf)
* запускаем скрипт сбора docker-compose.yml ```python3 make_docker_compose.py```

Параметры конфигурационного файла:


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

