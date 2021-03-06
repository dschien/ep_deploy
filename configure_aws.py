import ConfigParser

import boto3
from fabric import colors
from fabric.api import *
from fabric.contrib.files import upload_template

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.update(config._sections['ec2'])
env.update(config._sections['ep_common'])
env.update(config._sections['db'])
env.update(config._sections['influxdb'])
env.update(config._sections['secure_server'])
env.update(config._sections['prefect'])
env.update(config._sections['messaging.iodicus.net'])


def prod():
    env.update(config._sections['energyportal'])
    env.log_group_name_ea = env.log_group_name + "/ea/prod"


def staging():
    env.update(config._sections['energyportal_staging'])
    env.log_group_name_ea = env.log_group_name + "/ea/staging"


def install_logs_agent():
    """
    This requires that EP instances have an IAM role with the following policy attached:
        {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ],
        "Resource": [
          "arn:aws:logs:*:*:*"
        ]
      }
     ]
    }

    :return:
    """
    run('curl https://s3.amazonaws.com/aws-cloudwatch/downloads/latest/awslogs-agent-setup.py -O')
    run('sudo python ./awslogs-agent-setup.py -o')


def configure_logs_agent():
    upload_template('awslogs.conf',
                    '/var/awslogs/etc/awslogs.conf',
                    use_sudo=True, template_dir='templates', use_jinja=True, context=env)
    sudo('sudo service awslogs restart')


def setup_alarms():
    create_celery_alive_alarm()
    create_secure_client_alive_alarm()
    create_email_on_error_log_alarm()


def create_email_on_error_log_alarm():
    metricsNamespace = 'LogMetrics'
    metricName = 'ErrorCount' + "_%(sys_type)s" % env

    print colors.cyan('Put metric $(metricName)s' % env)

    cloudwatch_client = boto3.client('cloudwatch')
    response = cloudwatch_client.put_metric_data(
        Namespace=metricsNamespace,
        MetricData=[
            {
                'MetricName': metricName,
                'Unit': 'Count',
                'Value': 1
            },
        ]
    )

    logs_client = boto3.client('logs')
    print colors.cyan('Put metric filter $.levelname-ERROR')
    logs_client.put_metric_filter(
        logGroupName=env.log_group_name_ea,
        filterName='levelname-ERROR',
        filterPattern='{ $.levelname = "ERROR" }',
        metricTransformations=[
            {
                'metricNamespace': metricsNamespace,
                'metricValue': '1',
                'metricName': metricName,
            }]

    )
    print colors.cyan('Put metric filter catchAll')
    logs_client.put_metric_filter(
        logGroupName=env.log_group_name_ea,
        filterName="catchAll",
        filterPattern='',
        metricTransformations=[
            {
                'metricNamespace': metricsNamespace,
                'metricValue': '0',
                'metricName': metricName,
            }]
    )

    print colors.cyan('Put metric alarm, email on error')

    response = cloudwatch_client.put_metric_alarm(
        AlarmName='email on error ' + "_%(sys_type)s" % env,
        AlarmDescription='email on error' + "_%(sys_type)s" % env,
        ActionsEnabled=True,

        AlarmActions=[
            env.aws_sns_arn_error_email,
        ],

        MetricName=metricName,
        Namespace=metricsNamespace,
        Statistic='Sum',
        Period=900,
        Unit='Count',
        EvaluationPeriods=1,
        Threshold=0,
        ComparisonOperator='GreaterThanThreshold'
    )


def create_celery_alive_alarm():
    _create_alive_log_missing_alarm(name='celery-worker-alive',
                                    filter_pattern='{ $.message = "celery worker alive" }')


def create_secure_client_alive_alarm():
    _create_alive_log_missing_alarm(name='secure-websocket-alive',
                                    filter_pattern='{ $.message = "Secure importer alive" }')


def _create_alive_log_missing_alarm(name, filter_pattern):
    metricsNamespace = 'LogMetrics'

    print colors.cyan('Put metric $(metricName)s' % env)

    cloudwatch_client = boto3.client('cloudwatch')
    metric_name = name + " %(sys_type)s" % env

    response = cloudwatch_client.put_metric_data(
        Namespace=metricsNamespace,
        MetricData=[
            {
                'MetricName': metric_name,
                'Unit': 'Count',
                'Value': 1
            },
        ]
    )

    logs_client = boto3.client('logs')
    print colors.cyan('Put metric filter: %s' % metric_name)
    logs_client.put_metric_filter(
        logGroupName=env.log_group_name_ea,
        filterName=name + "_%(sys_type)s" % env,
        filterPattern=filter_pattern,
        metricTransformations=[
            {
                'metricNamespace': metricsNamespace,
                'metricValue': '1',
                'metricName': metric_name,
            }]

    )

    print colors.cyan('Put metric alarm %s' % name)

    cloudwatch_client.put_metric_alarm(
        AlarmName='email {} {}'.format(env.sys_type, name),
        AlarmDescription='email {} {}'.format(env.sys_type, name),
        ActionsEnabled=True,

        AlarmActions=[
            env.aws_sns_arn_error_email,
        ],

        MetricName=metric_name,
        Namespace=metricsNamespace,
        Statistic='Sum',
        Period=300,
        Unit='Count',
        EvaluationPeriods=1,
        Threshold=0,
        ComparisonOperator='LessThanOrEqualToThreshold'
    )


def create_cpu_alarm():
    client = boto3.client('cloudwatch')

    response = client.put_metric_alarm(
        AlarmName='cpu-mon-%(instance_id)s' % env,
        AlarmDescription='Alarm when CPU exceeds 70 percent',
        ActionsEnabled=True,

        AlarmActions=[
            env.aws_sns_arn_error_email,
        ],

        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistic='Average',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': '%(instance_id)s' % env
            },
        ],
        Period=300,
        Unit='Percent',
        EvaluationPeriods=2,
        Threshold=70,
        ComparisonOperator='GreaterThanThreshold'
    )


def create_memory_alarm(instance_id):
    client = boto3.client('cloudwatch')
    instance_id = {'instance_id': instance_id if instance_id else env['instance_id']}
    response = client.put_metric_alarm(
        AlarmName='memory-mon-%(instance_id)s' % instance_id,
        AlarmDescription='Alarm when memory exceeds 70 percent',
        ActionsEnabled=True,

        AlarmActions=[
            env.aws_sns_arn_error_email,
        ],

        MetricName='MemoryUtilization',
        Namespace='System/Linux',
        Statistic='Average',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': '%(instance_id)s' % instance_id
            },
        ],
        Period=300,
        Unit='Percent',
        EvaluationPeriods=2,
        Threshold=70,
        ComparisonOperator='GreaterThanThreshold'
    )


def create_RDS_instance():
    """
    http://boto3.readthedocs.org/en/latest/reference/services/rds.html#RDS.Client.create_db_instance
    :return:
    """
    client = boto3.client('rds')
    response = client.create_db_instance(
        DBName=env.db_name,
        DBInstanceIdentifier=env.db_instance_id + "-%(sys_type)s" % env,
        AllocatedStorage=16,
        DBInstanceClass='db.t1.micro',
        Engine='postgres',
        MasterUsername=env.db_master_username,
        MasterUserPassword=env.db_masteruserpassword,
        # DBSecurityGroups=[
        #     'string',
        # ],
        VpcSecurityGroupIds=[
            env.db_vpcsecuritygroupid,
        ],
        AvailabilityZone='eu-west-1a',
        DBSubnetGroupName='default',
        # PreferredMaintenanceWindow='string',
        # DBParameterGroupName='string',
        BackupRetentionPeriod=14,
        # PreferredBackupWindow='string',
        Port=5432,
        MultiAZ=False,
        EngineVersion='9.4.5',
        AutoMinorVersionUpgrade=True,
        LicenseModel='postgresql-license',
        # Iops=123,
        # OptionGroupName='string',
        # CharacterSetName='string',
        PubliclyAccessible=False,
        # Tags=[
        #     {
        #         'Key': 'string',
        #         'Value': 'string'
        #     },
        # ],
        # DBClusterIdentifier='string',
        StorageType='standard',
        # TdeCredentialArn='string',
        # TdeCredentialPassword='string',
        StorageEncrypted=False,
        # KmsKeyId='string',
        # Domain='string',
        # CopyTagsToSnapshot=True | False,
        # MonitoringInterval=123,
        # MonitoringRoleArn='string',
        # DomainIAMRoleName='string'
    )


def configure_local_settings():
    # get IP of influxdb host
    instance_name = "influxdb"

    influxdb_ip = get_instance_private_ip(instance_name)

    env['influx_db_host'] = influxdb_ip

    import random
    env.secret_key = ''.join(
        [random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    upload_template('local_settings.py',
                    '/home/ubuntu/ep_site/local_settings.py',
                    use_sudo=True, template_dir='templates', use_jinja=True, context=env)


def get_instance_private_ip(instance_name):
    instance = get_instance_by_name(instance_name)
    influxdb_ip = instance.private_ip_address
    return influxdb_ip


def get_instance_by_name(instance_name):
    import boto.ec2
    REGION = config.get('ec2', 'REGION')
    conn = boto.ec2.connect_to_region(REGION)
    reservations = conn.get_all_instances(filters={"tag:Name": instance_name})
    instances = [i for r in reservations for i in r.instances]
    assert len(instances) == 1
    return instances[0]


def configure_docker_env():
    upload_template('docker-env',
                    '/home/ubuntu/ep_site/etc/docker-env',
                    use_sudo=True, template_dir='templates', use_jinja=True, context=env)


def configure():
    configure_local_settings()
    configure_docker_env()


def _marker(marker):
    return ' # MARKER:%s' % marker if marker else ''


def _get_current():
    with settings(hide('warnings', 'stdout'), warn_only=True):
        output = run('crontab -l')
        return output if output.succeeded else ''


def crontab_set(content):
    """ Sets crontab content """
    run("echo '%s'|crontab -" % content)


def crontab_show():
    """ Shows current crontab """
    puts(_get_current())


def crontab_add(content, marker=None):
    """ Adds line to crontab. Line can be appended with special marker
    comment so it'll be possible to reliably remove or update it later. """
    old_crontab = _get_current()
    crontab_set(old_crontab + '\n' + content + _marker(marker))


def crontab_remove(marker):
    """ Removes a line added and marked using crontab_add. """
    lines = [line for line in _get_current().splitlines()
             if line and not line.endswith(_marker(marker))]
    crontab_set("\n".join(lines))


def crontab_update(content, marker):
    """ Adds or updates a line in crontab. """
    crontab_remove(marker)
    crontab_add(content, marker)


def install_aws_log_agent():
    """
    Following this guide: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/mon-scripts.html
    :return:
    """
    run('sudo apt-get update')
    run('sudo apt-get -y install unzip')
    run('sudo apt-get -y install libwww-perl libdatetime-perl')
    run('curl http://aws-cloudwatch.s3.amazonaws.com/downloads/CloudWatchMonitoringScripts-1.2.1.zip -O')
    run('unzip CloudWatchMonitoringScripts-1.2.1.zip')
    run('rm CloudWatchMonitoringScripts-1.2.1.zip')
    run('cd aws-scripts-mon')
    crontab_add(
        '*/5 * * * * ~/aws-scripts-mon/mon-put-instance-data.pl --mem-util --disk-space-util --disk-path=/ --from-cron')
