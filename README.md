# Energy Aggregator Deployment Scripts
Requires `python 2.7`, `fabric` and `boto3`

# Development
To update git and restart containers use:
`fab prod update_site` or `fab staging update_site`

# Deployment

## Edit 
`ep.cfg` 

## Deploy nginx conf and server certificates
`fab -f fabfile-deploy-ep.py config_nginx`
### probably change hostname too
`fab -f fabfile-deploy-ep.py change_hostname`

## Configure AWS CloudWatch
1. Create SNS topic and subscription
2. create email on error alerts
`fab -f configure_aws.py prod create_email_on_error_log_alarm`
- watch celery log
`fab -f configure_aws.py prod create_email_on_celery_off_log_alarm`

 
