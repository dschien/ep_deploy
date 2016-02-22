__author__ = 'schien'

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