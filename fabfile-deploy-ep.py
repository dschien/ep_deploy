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


def config_nginx():
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
