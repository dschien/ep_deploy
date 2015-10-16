__author__ = 'schien'

from fabric.api import *

GIT_ORIGIN = "git@github.com"

# The git repo is the repo we should clone
GIT_REPO = "dschien/ep_site.git"

# env.hosts = ['52.18.118.168']

DB_ENDPOINT = 'ep.cg45k2qrlqro.eu-west-1.rds.amazonaws.com'

# The hosts we need to configure
HOSTS = ["ec2-52-17-239-200.eu-west-1.compute.amazonaws.com"]


#### Environments

def production():
    "Setup production settings"
    env.hosts = HOSTS
    env.repo = ("env.example.com", "origin", "release")
    env.virtualenv, env.parent, env.branch = env.repo
    env.base = "/opt"
    env.user = "ubuntu"
    env.git_origin = GIT_ORIGIN
    env.git_repo = GIT_REPO
    env.dev_mode = False
    env.key_filename = '~/.ssh/ep-host.pem'


def sub_git_clone():
    "Clones a repository into the virtualenv at /project"
    run(
        "cd %(base)s/%(virtualenv)s; git clone %(git_origin)s:%(git_repo)s project; cd project; git checkout %(branch)s; git pull %(parent)s %(branch)s" % env)


def install_make_tools():
    run('sudo apt-get update')
    run('sudo apt-get -y install build-essential')


def install_py35():
    run('sudo add-apt-repository ppa:fkrull/deadsnakes')
    run('sudo apt-get update')
    run('sudo apt-get -y install python3.5')
    run('sudo apt-get -y install python3.5-venv')
    run('sudo apt-get -y install python3.5-dev')
    run('sudo apt-get -y install libfreetype6-dev')
    run('sudo apt-get -y install libxft-dev')
    run('sudo apt-get -y install libpq-dev')


def install_webstack():
    run('sudo apt-get -y install nginx')


def install_numpy():
    with prefix('source ep-venv/bin/activate'):
        run('pip install "ipython[notebook]"')


def clone_git():
    with cd('/opt'):
        run('git ')


def deploy():
    install_make_tools()
    install_py35()
    install_rabbit()
    clone_git()
    install_py_deps()


def install_rabbit():
    run('sudo apt-get -y install rabbitmq-server')


def create_virtualenv():
    run('pyvenv-3.5 ep-venv')


def install_py_deps():
    with prefix('source ep-venv/bin/activate'):
        run('pip install -r requirements.txt')


def copy_projects():
    with cd('coms20805'):
        run('git pull')
        run('cp -R client_projects_2015/ /home/web/HTML/Teaching/Resources/COMS20805')


def sub_get_requirements():
    "Gets the requirements for the project"
    sudo("cd %(base)s/%(virtualenv)s; source bin/activate; pip install -r project/requirements.txt" % env)


