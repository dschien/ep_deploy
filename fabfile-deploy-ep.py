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
env.user = config.get('ep_common', 'USER')
# env.hosts = [config.get('energyportal_staging', 'host')]
# env.host = env.hosts[0]

env.key_filename = config.get('ep_common', 'key_path')


#### Environments


def production():
    "Setup production settings"
    # check_or_start_instance()
    env.repo = ("ep-venv", "origin", "release")
    env.virtualenv, env.parent, env.branch = env.repo
    env.base = "/opt"
    env.git_origin = GIT_ORIGIN
    env.git_repo = GIT_REPO
    env.dev_mode = False


def change_hostname():
    run('cat %s > /etc/hostname' % env.host)


def config_nginx():
    upload_template('nginx.conf',
                    '/etc/nginx/nginx.conf',
                    use_sudo=True, template_dir='templates/')
    if not exists('/etc/nginx/sites-enabled/'):
        sudo('mkdir /etc/nginx/sites-enabled/')
    upload_template('docker_unicorn.conf',
                    '/etc/nginx/sites-enabled/docker_unicorn.conf',
                    use_sudo=True, template_dir='templates/', use_jinja=True, context=env)

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
