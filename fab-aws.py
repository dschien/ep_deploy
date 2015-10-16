__author__ = 'schien'


import os, time, boto
import ConfigParser

CONFIG_FILE = "ep.cfg"

MAVERIK_64 = "ami-688c7801"
MAVERIK_32 = "ami-1a837773"
LUCID_64 = "ami-da0cf8b3"
LUCID_32 = "ami-a403f7cd"

config = ConfigParser.RawConfigParser()

# If there is no config file, let's write one.
if not os.path.exists(CONFIG_FILE):
    config.add_section('ec2')
    config.set('ec2', 'AMI', LUCID_32)
    config.set('ec2', 'INSTANCE_TYPE', 'm1.small')
    config.set('ec2', 'SECURITY_GROUP', 'geonode')
    config.set('ec2', 'KEY_PATH', 'geonode.pem')
    config.set('ec2', 'AWS_ACCESS_KEY_ID', '')
    config.set('ec2', 'AWS_SECRET_ACCESS_KEY', '')
    config.set('ec2', 'USER', 'ubuntu')

    # Writing our configuration file to CONFIG_FILE
    with open(CONFIG_FILE, 'wb') as configfile:
        config.write(configfile)
else:
    config.read(CONFIG_FILE)

MY_AMI = config.get('ec2', 'AMI')
SECURITY_GROUP = config.get('ec2', 'SECURITY_GROUP')
KEY_PATH = config.get('ec2', 'KEY_PATH')
INSTANCE_TYPE = config.get('ec2', 'INSTANCE_TYPE')

os.environ["AWS_ACCESS_KEY_ID"] = config.get('ec2', 'AWS_ACCESS_KEY_ID')
os.environ["AWS_SECRET_ACCESS_KEY"] = config.get('ec2', 'AWS_SECRET_ACCESS_KEY')

host = None
try:
    host = config.get('ec2', 'HOST')
except:
    pass

if host is not None and host != '':
    env.hosts = [host, ]
    env.user = config.get('ec2', 'USER')
    env.key_filename = KEY_PATH
    print "Instance already created, using it: %s" % host
else:
    conn = boto.connect_ec2()
    image = conn.get_image(MY_AMI)
    security_groups = conn.get_all_security_groups()

    try:
        [geonode_group] = [x for x in security_groups if x.name == SECURITY_GROUP]
    except ValueError:
        # this probably means the security group is not defined
        # create the rules programatically to add access to ports 22, 80, 8000 and 8001
        geonode_group = conn.create_security_group(SECURITY_GROUP, 'Cool GeoNode rules')
        geonode_group.authorize('tcp', 22, 22, '0.0.0.0/0')
        geonode_group.authorize('tcp', 80, 80, '0.0.0.0/0')
        geonode_group.authorize('tcp', 8000, 8001, '0.0.0.0/0')
        geonode_group.authorize('tcp', 8080, 8080, '0.0.0.0/0')

    try:
        [geonode_key] = [x for x in conn.get_all_key_pairs() if x.name == 'geonode']
    except ValueError:
        # this probably means the key is not defined
        # get the first one in the belt for now:
        print "GeoNode file not found in the server"
        geonode_key = conn.get_all_key_pairs()[0]

    reservation = image.run(security_groups=[geonode_group, ], key_name=geonode_key.name, instance_type=INSTANCE_TYPE)
    instance = reservation.instances[0]

    print "Firing up instance"

    # Give it 10 minutes to appear online
    for i in range(120):
        time.sleep(5)
        instance.update()
        print instance.state
        if instance.state == "running":
            break

    if instance.state == "running":
        dns = instance.dns_name
        print "Instance up and running at %s" % dns

    config.set('ec2', 'HOST', dns)
    config.set('ec2', 'INSTANCE', instance.id)
    env.hosts = [dns, ]
    env.user = config.get('ec2', 'USER')
    env.key_filename = KEY_PATH
    with open(CONFIG_FILE, 'wb') as configfile:
        config.write(configfile)

    print "ssh -i %s ubuntu@%s" % (KEY_PATH, dns)
    print "Terminate the instance via the web interface %s" % instance

time.sleep(20)
