import os
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'env.conf')
from clickhouse_driver import Client as click_client

def parse_parameters(filename='./env.conf'):
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

def create_table(client, table_name, columns_types, time_col=None, topic=''):
    client.execute(f"DROP IF EXISTS TABLE {table_name}")
    client.execute(f"DROP IF EXISTS TABLE {table_name}_in")
    client.execute(f"DROP IF EXISTS TABLE {table_name}_mv")

    dtypes = ''
    for col, t in columns_types:
        dtypes += f'    {col} {t},\n'

    # Создаём таблицу выхода
    query = f"""
CREATE TABLE {table_name}
(
    {dtypes.strip()[:-1]}
)"""
    if time_col is not None:
        query += f""" ENGINE = MergeTree()
  PARTITION BY toYYYYMM({time_col})
  PRIMARY KEY {time_col}
  ORDER BY {time_col}
  SETTINGS index_granularity = 8192;
"""
    else:
        query += ' ENGINE = Memory;'
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
    config = parse_parameters(CONFIG_PATH)

    cclient = click_client(host=config['CLICKHOUSE_HOST'], port=config['CLICKHOUSE_PORT'], settings={'use_numpy': True})
    cclient=None

    # browser_events
    dtypes = [
        ('event_id', 'String'),
        ('event_timestamp', 'DateTime64'),
        ('event_type', 'String'),
        ('click_id', 'String'),
        ('browser_name', 'String'),
        ('browser_user_agent', 'String'),
        ('browser_language', 'String'),
    ]
    create_table(cclient, config['BROWSER_EVENTS_TABLE'], dtypes, 'event_timestamp', config['BROWSER_EVENTS_TOPIC'])

    # device_events
    dtypes = [
        ('click_id', 'String'),
        ('os', 'String'),
        ('os_name', 'String'),
        ('os_timezone', 'String'),
        ('device_type', 'String'),
        ('device_is_mobile', 'Boolean'),
        ('user_custom_id', 'String'),
        ('user_domain_id', 'String'),
    ]
    create_table(cclient, config['DEVICE_EVENTS_TABLE'], dtypes, topic=config['DEVICE_EVENTS_TOPIC'])

    # geo_events
    dtypes = [
        ('click_id', 'String'),
        ('geo_latitude', 'Float32'),
        ('geo_longitude', 'Float32'),
        ('geo_country', 'String'),
        ('geo_timezone', 'String'),
        ('geo_region_name', 'String'),
        ('ip_address', 'String'),
    ]
    create_table(cclient, config['GEO_EVENTS_TABLE'], dtypes, topic=config['GEO_EVENTS_TOPIC'])

    # location_events
    dtypes = [
        ('click_id', 'String'),
        ('page_url', 'String'),
        ('page_url_path', 'String'),
        ('referer_url', 'String'),
        ('referer_medium', 'String'),
        ('utm_medium', 'String'),
        ('utm_source', 'String'),
        ('utm_content', 'String'),
        ('utm_campaign', 'String'),
    ]
    create_table(cclient, config['GEO_EVENTS_TABLE'], dtypes, topic=config['GEO_EVENTS_TOPIC'])
