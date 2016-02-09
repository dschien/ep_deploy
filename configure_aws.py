import ConfigParser
import os

from fabric import colors
from fabric.contrib.files import upload_template
from fabric.utils import apply_lcwd
from fabric.api import *
import boto3

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.update(config._sections['ep_common'])
env.log_group_name_ea = env.log_group_name + "/ea"


def prod():
    env.update(config._sections['energyportal'])


def staging():
    env.update(config._sections['energyportal_staging'])


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
        AlarmName='email on error',
        AlarmDescription='email on error',
        ActionsEnabled=True,

        AlarmActions=[
            env.aws_sns_arn_error_email,
        ],

        MetricName=metricName,
        Namespace=metricsNamespace,
        Statistic='Sum',
        Period=300,
        Unit='Count',
        EvaluationPeriods=1,
        Threshold=0,
        ComparisonOperator='GreaterThanThreshold'
    )


def create_email_on_celery_off_log_alarm():
    metricsNamespace = 'LogMetrics'
    metricName = 'celery-worker-alive' + "_%(sys_type)s" % env

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
    print colors.cyan('Put metric filter celery alive')
    logs_client.put_metric_filter(
        logGroupName=env.log_group_name_ea,
        filterName='celery-worker-alive',
        filterPattern='{ $.message = "celery worker alive" }',
        metricTransformations=[
            {
                'metricNamespace': metricsNamespace,
                'metricValue': '1',
                'metricName': metricName,
            }]

    )

    print colors.cyan('Put metric alarm, email on error')

    response = cloudwatch_client.put_metric_alarm(
        AlarmName='email on not alive',
        AlarmDescription='email on not alive',
        ActionsEnabled=True,

        AlarmActions=[
            env.aws_sns_arn_error_email,
        ],

        MetricName=metricName,
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
