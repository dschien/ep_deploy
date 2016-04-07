__author__ = 'schien'

import configparser, itertools, os

CONFIG_FILE = "etc/docker-env"
cfg = configparser.ConfigParser()
cfg.read_file(itertools.chain(['[global]'], open(CONFIG_FILE)))
config = cfg['global']

# Make this unique, and don't share it with anybody.
SECRET_KEY = '{{ secret_key }}'

# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''

# for deployment without authentication
AWS_ACCESS_KEY_ID = '{{ aws_access_key_id }}'
AWS_SECRET_ACCESS_KEY = '{{ aws_secret_access_key }}'

IODICUS_MESSAGING_PASSWORD = '{{ messaging_password }}'

SECURE_SERVER_URL = '{{ secure_server_url }}'
SECURE_SERVER_USER = '{{ secure_server_user }}'
SECURE_SERVER_PASSWORD = '{{ secure_server_password }}'

DB_HOST = '{{ db_host }}'
DB_PASSWORD = '{{ db_masteruserpassword }}'
DB_USER = '{{ db_master_username }}'

MEMCACHE_HOST = 'memcache:11211'

INFLUXDB_PASSWORD = config['INFLUXDB_INIT_PWD']
INFLUXDB_USER = config['ADMIN_USER']
INFLUX_DB_NAME = config['PRE_CREATE_DB']
INFLUXDB_PORT = 8086
INFLUXDB_HOST = '{{ influx_db_host }}'

LOG_LEVEL = '{{ log_level }}'
