# Prerequisits to using Energy Aggregator Deployment Scripts
Requires `python 2.7`, `fabric` and `boto3`

# Deployment

## Edit `ep.cfg` for passwords 
`ep.cfg` 

## Deployment 
*replace staging with prod if necessary* 
install nginx, docker; conf and server certificates
`fab -f fabfile-deploy-ep staging deploy`
`fab -f fabfile-deploy-ep staging configure_docker`
- configure NGINX
`fab -f fabfile-deploy-ep.py config_nginx`
`fab -f fabfile-deploy-ep staging clone`
`fab staging complete_update`
- change hostname
`fab -f fabfile-deploy-ep.py change_hostname`
`fab staging initial_container_deployment`
- configure EA
`fab -f configure_aws.py staging configure_docker_env`
`fab -f configure_aws.py staging configure_local_settings`
`fab staging restart_containers`



## Configure AWS CloudWatch
1. Create SNS topic and subscription
2. create email on error alerts
`fab -f configure_aws.py prod create_email_on_error_log_alarm`
- watch celery log
`fab -f configure_aws.py prod create_email_on_celery_off_log_alarm`


# Development tasks
To update git and restart containers use:
`fab prod update_site` or `fab staging update_site`


 
