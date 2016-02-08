import ConfigParser
import logging

from fabric.api import *

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.forward_agent = True
KEY_PATH = config.get('energyportal', 'KEY_PATH')
env.key_filename = KEY_PATH
# env.hosts = [config.get('energyportal', 'host')]
env.user = config.get('energyportal', 'USER')


def staging():
    env.hosts = ['52.49.146.206']


def update():
    with cd('ep_site'):
        run('git pull')


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

container_state = {'RUNNING': 1, 'STOPPED': 2, 'NOT_FOUND': 3}


# docker inspect --format="{{ .State.StartedAt }}" $CONTAINER)
# NETWORK=$(docker inspect --format="{{ .NetworkSettings.IPAddress }}" $CONTAINER
def inspect_container(container_name_or_id=''):
    """ e.g. fab --host ep.iodicus.net inspect_container:container_name_or_id=... """
    with settings(warn_only=True):
        result = run("docker inspect --format '{{ .State.Running }}' " + container_name_or_id)
        running = (result == 'true')
    if result.failed:
        logger.warn('inspect_container failed for container {}'.format(container_name_or_id))
        return container_state['NOT_FOUND']
    if not running:
        logger.info('container {} stopped'.format(container_name_or_id))
        return container_state['STOPPED']
    logger.info('container {} running'.format(container_name_or_id))
    return container_state['RUNNING']



    # container_started_at = run("docker inspect --format '{{ .State.StartedAt }}' " + container_name_or_id)
    # container_IP = run("docker inspect --format '{{ .NetworkSettings.IPAddress }}' " + container_name_or_id)
    #


def stop_container(container_name_or_id=''):
    with settings(warn_only=True):
        result = run("docker stop " + container_name_or_id)
        if not result.failed:
            logger.info('container {} stopped'.format(container_name_or_id))


def remove_container(container_name_or_id=''):
    with settings(warn_only=True):
        result = run("docker rm " + container_name_or_id)
        if result == container_name_or_id:
            logger.info('container {} removed'.format(container_name_or_id))
        else:
            logger.warn('unexpect command result, check log output')


def start_web():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                "docker run --name web -h ep  -d -p 8000:8000 --link rabbit --link db:db -v `pwd`:/ep_site -w /ep_site dschien/web deployment/docker-web-prod/entrypoint.sh")
            if not result.failed:
                logger.info('container web started')


def docker_logs(container_name_or_id=''):
    with settings(warn_only=True):
        run('docker logs --tail 50 -f {}'.format(container_name_or_id))


def start_celery_worker():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -h ep --name celery_worker -e "C_FORCE_ROOT=true" -p 5555:5555 -d --link rabbit --link db:db -v `pwd`:/ep_site -w /ep_site dschien/web celery -A ep_site worker -l info'
            )
            if not result.failed:
                logger.info('container celery_worker started')


def start_celery_beat():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -d -h ep --name celery_beat -e "C_FORCE_ROOT=true" -d --link rabbit --link db:db -v `pwd`:/ep_site -w /ep_site dschien/web celery -A ep_site beat'
            )
            if not result.failed:
                logger.info('container celery_beats started')


def recreate_db():
    with settings(warn_only=True):
        with cd('ep_site'):
            run('docker stop db')
            run('docker rm db')
            run('docker rm pg_data')
            run('docker create -v /var/lib/postgresql/data --name pg_data busybox')
            run('docker run -p 5432:5432 --name db --env-file etc/env -d --volumes-from pg_data_test postgres:9.4')


def redeploy_container(container_name_or_id=''):
    """ e.g. fab --host ep.iodicus.net inspect_container:container_name_or_id=... """
    state = inspect_container(container_name_or_id)
    if state == container_state['RUNNING']:
        stop_container(container_name_or_id)
    remove_container(container_name_or_id)
    if container_name_or_id == 'web':
        start_web()
    if container_name_or_id == 'celery_worker':
        start_celery_worker()
    if container_name_or_id == 'celery_beat':
        start_celery_beat()


def update_site():
    """
    Pull from git and restart docker containers
    :return:
    """
    update()

    for container in ['web', 'celery_worker', 'celery_beat']:
        redeploy_container(container)
