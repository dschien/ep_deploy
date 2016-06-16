import ConfigParser

from fabric.contrib.files import exists, upload_template

__author__ = 'schien'

from fabric.api import *

GIT_ORIGIN = "git@github.com"

# The git repo is the repo we should clone
GIT_REPO = "dschien/ep_site.git"

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.update(config._sections['ep_common'])


# env.hosts = [config.get('energyportal_staging', 'host')]
# env.host = env.hosts[0]

def prod():
    env.update(config._sections['energyportal'])


def staging():
    env.update(config._sections['energyportal_staging'])


def change_hostname():
    run('cat %s > /etc/hostname' % env.host)


def clone():
    run('git clone --recursive git@github.com:dschien/ep_site.git')
    with cd('ep_site'):
        run('mkdir log')


def deploy():
    """
    install docker and nginx
    :return:
    """
    sudo('apt-get update')
    sudo('apt-get -y install nginx')
    sudo('apt-get -y install apt-transport-https ca-certificates')
    sudo(
        'apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D')
    sudo(
        'echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" | sudo tee /etc/apt/sources.list.d/docker.list')
    sudo('apt-get update')
    sudo('apt-get -y install docker-engine')


def configure_docker():
    """
    option
    :return:
    """
    sudo('groupadd docker')
    sudo('usermod -aG docker ubuntu')


def install_python():
    sudo('apt-get install libbz2-dev')
    run('mkdir -p local/python-3.5.1')
    run('wget https://www.python.org/ftp/python/3.5.1/Python-3.5.1.tgz')
    run('tar -zxvf Python-3.5.1.tgz')
    with cd('Python-3.5.1'):
        run('./configure --prefix=$HOME/local/python-3.5.1/ --enable-ipv6')
        run('make')
        run('make install')

    run('~/local/python-3.5.1/bin/pyvenv venv35')

    sudo('apt-get -y install libmemcached-dev')

def config_nginx(regen_dhparm=False):
    if regen_dhparm:
        with cd('/etc/ssl/certs'):
            sudo('openssl dhparam -out dhparam.pem 4096')

    template_dir = 'templates/'
    upload_template('nginx.conf',
                    '/etc/nginx/nginx.conf',
                    use_sudo=True, template_dir=template_dir)
    if not exists('/etc/nginx/sites-enabled/'):
        sudo('mkdir /etc/nginx/sites-enabled/')
    upload_template('docker_gunicorn.conf',
                    '/etc/nginx/sites-enabled/docker_gunicorn.conf',
                    use_sudo=True, template_dir=template_dir, use_jinja=True, context=env, backup=False)

    if not exists('/etc/nginx/ssl/'):
        sudo('mkdir /etc/nginx/ssl/')
    upload_template(
        '/Users/csxds/Documents/iodicus-certs/2nd_iodicus_signing_request/prepare_for_deployment/iodicus_net.bundle.crt',
        '/etc/nginx/ssl/%(ssl_cert_bundle_target_filename)s' % env,
        use_sudo=True)
    upload_template(
        '/Users/csxds/Documents/iodicus-certs/2nd_iodicus_signing_request/prepare_for_deployment/iodicus_net.key',
        '/etc/nginx/ssl/%(ssl_cert_key_target_filename)s' % env,
        use_sudo=True)

    sudo('service nginx restart')
