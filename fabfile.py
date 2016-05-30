import ConfigParser
import logging

from fabric.api import *

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.forward_agent = True
env.update(config._sections['ep_common'])


def prod():
    env.update(config._sections['energyportal'])


def staging():
    env.update(config._sections['energyportal_staging'])


def update():
    with cd('ep_site'):
        run('git pull --recurse-submodules')
        run('git submodule init')
        run('git submodule update')
        # run('git submodule foreach git pull origin master')


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
                "docker run --name web -h %(sys_type)s  -d -p 8000:8000 --env CONTAINER_NAME=web --link rabbit --link memcache  -v `pwd`:/ep_site -w /ep_site dschien/web deployment/docker-web-prod/entrypoint.sh" % env)
            if not result.failed:
                logger.info('container web started')


def docker_logs(container_name_or_id=''):
    with settings(warn_only=True):
        run('docker logs --tail 50 -f {}'.format(container_name_or_id))


def start_celery_worker():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -h %(sys_type)s --name celery_worker -e "C_FORCE_ROOT=true" -p 5555:5555 --env CONTAINER_NAME=celery_worker -d  --link rabbit --link memcache  -v `pwd`:/ep_site -w /ep_site dschien/web celery -A ep_site worker -l info' % env
            )
            if not result.failed:
                logger.info('container celery_worker started')


def start_celery_beat():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -d -h %(sys_type)s --name celery_beat -e "C_FORCE_ROOT=true" -d  --link rabbit --link memcache --env CONTAINER_NAME=celery_beat -v `pwd`:/ep_site -w /ep_site dschien/web celery -A ep_site beat' % env
            )
            if not result.failed:
                logger.info('container celery_beats started')


def start_rabbit():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -d --volumes-from celery_rabbit_data --hostname rabbit --name rabbit rabbitmq:3'
            )
            if not result.failed:
                logger.info('container rabbit started')


def start_memcache():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -p 11211:11211 --name memcache -d memcached'
            )
            if not result.failed:
                logger.info('container memcache started')


def start_db():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -p 5432:5432 --name db%(db_suffix)s --env-file=etc/docker-env -d --volumes-from pg_data%(db_suffix)s postgres:9.4' % env
            )
            if not result.failed:
                logger.info('container db started')


def start_influxdb():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                # 'docker run -p 5432:5432 --name db%(db_suffix)s --env-file etc/docker-env -d --volumes-from pg_data%(db_suffix)s postgres:9.4' % env
                'docker run -d -p 8083:8083 -p 8086:8086 --env-file=etc/docker-env --name influxdb --volumes-from influxdb_data dschien/influxdb:latest' % env
            )
            if not result.failed:
                logger.info('container db started')


def start_grafana():
    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                'docker run -d -p 3000:3000  --env-file=etc/docker-env  --name grafana --volumes-from grafana_data grafana/grafana:latest' % env
            )
            if not result.failed:
                logger.info('container grafana started')


def start_websocket_client():
    container_name_or_id = 'secure_import'
    state = inspect_container(container_name_or_id)
    if state == container_state['RUNNING']:
        stop_container(container_name_or_id)
    remove_container(container_name_or_id)

    with settings(warn_only=True):
        with cd('ep_site'):
            result = run(
                "docker run -d -h %(sys_type)s --name secure_import -P  --link rabbit --link memcache  -v `pwd`:/ep_site --env CONTAINER_NAME=secure_client -w /ep_site dschien/web python manage.py import_secure_autobahn -r" % env)
            # "docker run -d -h %(sys_type)s --name secure_import -P --link db%(db_suffix)s:db -v `pwd`:/ep_site -w /ep_site dschien/web python manage.py import_secure" % env)
            if not result.failed:
                logger.info('container websock client started')


def recreate_db():
    with settings(warn_only=True):
        with cd('ep_site'):
            run('docker stop db')
            run('docker rm db')
            run('docker rm pg_data')
            run('docker create -v /var/lib/postgresql/data --name pg_data%(db_suffix)s busybox' % env)
            run(
                'docker run -p 5432:5432 --name db%(db_suffix)s --env-file=etc/docker-env -d --volumes-from pg_data%(db_suffix)s postgres:9.4' % env)


def rebuild_container():
    # with cd('ep_site/deployment/influx/0.10'):
    #     run('docker build -t dschien/influxdb .')
    #     run('docker create --volume=/data --name influxdb_data busybox')
    with cd('ep_site/deployment/docker-web'):
        run('docker build -t dschien/web-bare .')
    with cd('ep_site/deployment/docker-web-prod'):
        run('docker build -t dschien/web .')


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
    if container_name_or_id == 'rabbit':
        start_rabbit()
    if container_name_or_id == 'db':
        start_db()
    if container_name_or_id == 'memcache':
        start_memcache()
    if container_name_or_id == 'influxdb':
        start_influxdb()
    if container_name_or_id == 'grafana':
        start_grafana()


def update_site(pull=True):
    """
    Pull from git and restart docker containers
    :return:
    """
    if pull:
        update()
    restart_containers()


def restart_containers():
    for container in ['web', 'celery_worker', 'celery_beat']:
        stop_container(container)

    for container in ['rabbit', 'memcache']:
        redeploy_container(container)

    for container in ['web', 'celery_worker', 'celery_beat']:
        redeploy_container(container)

    start_websocket_client()


def start_local_containers():
    local('docker run -d --hostname rabbit --name rabbit rabbitmq:3')
    local('docker run -p 5432:5432 --name db --env-file=etc/docker-env -d --volumes-from pg_data postgres:9.4')
    local('docker run -p 11211:11211 --name memcache -d memcached')


def complete_update():
    update()
    rebuild_container()
    update_site()


def initial_container_deployment():
    run('docker create -v /var/lib/rabbitmq --name celery_rabbit_data busybox')
