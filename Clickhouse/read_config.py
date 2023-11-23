"""
Тулза для чтения конфига
"""
import os
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'env.conf')


def parse_parameters(filename=CONFIG_PATH):
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
    config = parse_parameters()
    for key, val in config.items():
        print(f'Параметр {key}={val}')