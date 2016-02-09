import ConfigParser
import os

from fabric.contrib.files import upload_template
from fabric.utils import apply_lcwd
from fabric.api import *
import boto3

CONFIG_FILE = "ep.cfg"
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

env.update(config._sections['ep_common'])


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

    upload_template('awslogs.conf',
                    '/var/awslogs/etc/awslogs.conf',
                    use_sudo=True, template_dir='templates', use_jinja=True, context=env)


def create_log_alarm_sdk():
    client = boto3.client('logs')
    logGroupName = 'ea_staging'

    client.put_metric_filter(
        logGroupName=logGroupName,
        filterName='levelname-ERROR',
        filterPattern='{ $.levelname = "ERROR" }',
        metricTransformations=[
            {
                'metricNamespace': 'LogMetrics',
                'metricValue': '0',
                'metricName': 'ErrorCount',
            }]

    )
    client.put_metric_filter(
        logGroupName=logGroupName,
        filterName='',
        filterPattern='',
        metricTransformations=[
            {
                'metricNamespace': 'LogMetrics',
                'metricValue': '1',
                'metricName': 'ErrorCount',
            }]
    )

    client = boto3.client('cloudwatch')

    response = client.put_metric_alarm(
        AlarmName='email on error',
        AlarmDescription='email on error',
        ActionsEnabled=True,

        AlarmActions=[
            env.AWS_SNS_ARN_error_email,
        ],

        MetricName='ErrorCount',
        Namespace='LogMetrics',
        Statistic='Sum',
        Period=300,
        Unit='Count',
        EvaluationPeriods=1,
        Threshold=0,
        ComparisonOperator='GreaterThanThreshold'
    )


def create_cpu_alarm():
    client = boto3.client()

    response = client.put_metric_alarm(
        AlarmName='cpu-mon-%(instance)s' % env,
        AlarmDescription='Alarm when CPU exceeds 70 percent',
        ActionsEnabled=True,
        OKActions=[
            'string',
        ],
        AlarmActions=[
            env.AWS_SNS_ARN_error_email,
        ],
        InsufficientDataActions=[
            'string',
        ],
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistic='Average',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': '%(instance)s' % env
            },
        ],
        Period=300,
        Unit='Percent',
        EvaluationPeriods=2,
        Threshold=70,
        ComparisonOperator='GreaterThanThreshold'
    )


def create_log_alarm_cli():
    template_dir = 'templates/'
    context = {'metricNamespace': 'LogMetrics',
               'metricValue': '0',
               'metricName': 'ErrorCount',
               'filterPattern': '{ $.levelname = "ERROR" }',
               'filterName': 'levelname-ERROR',
               'logGroupName': 'ea_staging'
               }
    template_file = 'aws_create_metric_cli_arg.json'

    text = render_template(context, template_dir, template_file)
    local('aws logs put-metric-filter --cli-input-json %s' % text.replace('\n', ''))


def render_template(context, template_dir, template_file):
    template_dir = template_dir or os.getcwd()
    template_dir = apply_lcwd(template_dir, env)
    from jinja2 import Environment, FileSystemLoader
    jenv = Environment(loader=FileSystemLoader(template_dir))
    text = jenv.get_template(template_file).render(**context or {})
    # Force to a byte representation of Unicode, or str()ification
    # within Paramiko's SFTP machinery may cause decode issues for
    # truly non-ASCII characters.
    text = text.encode('utf-8')
    return text
