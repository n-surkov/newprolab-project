"""
Скрипт отправки тестовых данных в Clickhouse
"""
from clickhouse_driver import Client as click_client
from read_config import parse_parameters
import time

WAITING_TIME = 5


def create_table(client, table_name, columns_types, topic=''):
    client.execute(f"DROP TABLE IF EXISTS {table_name}")
    client.execute(f"DROP TABLE IF EXISTS {table_name}_in")
    client.execute(f"DROP TABLE IF EXISTS {table_name}_mv")

    dtypes = ''
    for col, t in columns_types:
        dtypes += f'    {col} {t},\n'

    # Создаём таблицу выхода
    query = f"""
CREATE TABLE {table_name}
(
    {dtypes.strip()[:-1]}
) ENGINE = MergeTree()
  PARTITION BY toYYYYMMDD(batch_time)
  PRIMARY KEY batch_time
  ORDER BY batch_time
  SETTINGS index_granularity = 8192;
"""

    print(f"Creating table {table_name}:")
    print(query)
    client.execute(query)

    if topic != '':
        # Создаём таблицу кафки
        query = f"""
CREATE TABLE {table_name}_in
(
    {dtypes.strip()[:-1]}
) ENGINE = Kafka SETTINGS kafka_broker_list = '{config['KAFKA_HOST']}:{config['KAFKA_PORT']}',
                        kafka_topic_list = '{topic}',
                        kafka_group_name = 'newprolab_cg',
                        kafka_format = 'JSONEachRow';
"""
        print(f"Creating table {table_name}:")
        print(query)
        client.execute(query)

        # Создаём вьюху перегона
        query = f"""
CREATE MATERIALIZED VIEW {table_name}_mv TO {table_name} AS
SELECT *
FROM {table_name}_in;
"""
        print(f"Creating table {table_name}:")
        print(query)
        client.execute(query)


if __name__=="__main__":
    config = parse_parameters()

    print(f"В БД Clickhouse {config['CLICKHOUSE_HOST']}:{config['CLICKHOUSE_CLIENT_PORT']} будут созданы/пересозданы следующие таблицы:")
    for key, val in config.items():
        if '_TABLE' in key:
            print(f'* {val}')


    print(f'Есть {WAITING_TIME} секунд на раздумье...')
    for i in range(WAITING_TIME):
        print(f'{i + 1}...')
        time.sleep(1)

    cclient = click_client(host=config['CLICKHOUSE_HOST'], port=config['CLICKHOUSE_CLIENT_PORT'], settings={'use_numpy': True})

    # browser_events
    browser_dtypes = [
        ('event_id', 'String'),
        ('event_timestamp', 'DateTime64'),
        ('event_type', 'String'),
        ('click_id', 'String'),
        ('browser_name', 'String'),
        ('browser_user_agent', 'String'),
        ('browser_language', 'String'),
        ('batch_time', 'DateTime'),
    ]
    create_table(cclient, config['BROWSER_EVENTS_TABLE'], browser_dtypes, config['BROWSER_EVENTS_TOPIC'])

    # device_events
    device_dtypes = [
        ('click_id', 'String'),
        ('os', 'String'),
        ('os_name', 'String'),
        ('os_timezone', 'String'),
        ('device_type', 'String'),
        ('device_is_mobile', 'Boolean'),
        ('user_custom_id', 'String'),
        ('user_domain_id', 'String'),
        ('batch_time', 'DateTime'),
    ]
    create_table(cclient, config['DEVICE_EVENTS_TABLE'], device_dtypes, topic=config['DEVICE_EVENTS_TOPIC'])

    # geo_events
    geo_dtypes = [
        ('click_id', 'String'),
        ('geo_latitude', 'Float32'),
        ('geo_longitude', 'Float32'),
        ('geo_country', 'String'),
        ('geo_timezone', 'String'),
        ('geo_region_name', 'String'),
        ('ip_address', 'String'),
        ('batch_time', 'DateTime'),
    ]
    create_table(cclient, config['GEO_EVENTS_TABLE'], geo_dtypes, topic=config['GEO_EVENTS_TOPIC'])

    # location_events
    location_dtypes = [
        ('event_id', 'String'),
        ('page_url', 'String'),
        ('page_url_path', 'String'),
        ('referer_url', 'String'),
        ('referer_medium', 'String'),
        ('utm_medium', 'String'),
        ('utm_source', 'String'),
        ('utm_content', 'String'),
        ('utm_campaign', 'String'),
        ('batch_time', 'DateTime'),
    ]
    create_table(cclient, config['LOCATION_EVENTS_TABLE'], location_dtypes, topic=config['LOCATION_EVENTS_TOPIC'])

    # Суммарная таблица событий
    keys = []
    agg_dtypes = []
    for k, v in browser_dtypes + device_dtypes + geo_dtypes + location_dtypes:
        if k in keys:
            continue
        keys.append(k)
        agg_dtypes.append((k, v))
    
    create_table(cclient, config['UNION_TABLE'], agg_dtypes)
