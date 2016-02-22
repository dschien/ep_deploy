import pika
from fabric.api import *
import logging
import ConfigParser

logger = logging.getLogger(__name__)

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.forward_agent = True
env.update(config._sections['ep_common'])
env.update(config._sections['messaging.iodicus.net'])


def prod():
    env.update(config._sections['energyportal'])


def staging():
    env.update(config._sections['energyportal_staging'])


def create_exchange():
    EXCHANGE_NAME = env.exchange_name

    channel, connection = get_connection()

    channel.exchange_declare(exchange=EXCHANGE_NAME,
                             type='fanout')

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=EXCHANGE_NAME,
                       queue=queue_name)

    print(' [*] Waiting for logs. To exit press CTRL+C')

    def callback(ch, method, properties, body):
        print(" [x] %r" % (body,))

    channel.basic_consume(callback,
                          queue=queue_name,
                          no_ack=True)

    channel.start_consuming()

    connection.close()


def get_connection():
    credentials = pika.PlainCredentials(env.rabbit_user, env.messaging_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        env.messaging_rabbit_host, int(env.messaging_rabbit_port),
        credentials=credentials,
        ssl=True
    ))
    channel = connection.channel()
    return channel, connection
