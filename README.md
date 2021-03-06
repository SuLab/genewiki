genewiki
========

The GeneWiki Project

### Overview
The code in this repo handles the automated updates of gene templates, and as well as the on-request article creation requests from the BioGPS plugin (http://biogps.org/genewikigenerator/).  Both types of edits are made under the ProteinBoxBot Wikipedia account.

### Project Setup

#### Server Dependencies

* `sudo apt-get update`
* `sudo apt-get upgrade`
* `sudo apt-get install build-essential python python-dev python-pip python-virtualenv libmysqlclient-dev git-core nginx supervisor rabbitmq-server graphviz libgraphviz-dev pkg-config libncurses5-dev`

* `mkdir webapps`
* `cd webapps`
* `git clone https://github.com/SuLab/genewiki.git`
* `cd genewiki`
* `git fetch --all`
* `git reset --hard origin/master`


#### virtualenv

A Python Virtual Environment is used to ensure that the application runs in an isolated and protected environment

* Create a new virtual environment: `sudo virtualenv /opt/genewiki-venv`
* Activate the environment `source /opt/genewiki-venv/bin/activate`

If you see `(genewiki-venv)` in front of your shell, this worked.

* `sudo /opt/genewiki-venv/bin/pip install -r requirements.txt`


#### Setup

The `config` directory in this project hosts template files and their location for nginx, gunicorn and supervisor
* Supervisor : Copy config/*.conf into /etc/supervisor/conf.d (must update permissions on conf.d)
* nginx : Copy config/default into /etc/nginx/conf.d (upd perm on conf.d to allow copy)
* copy config/gunicorn_start into /bin


#### Configuration

The settings files are not included in the repo for security reasons and must be uploaded to the server.

* `sudo adduser deploy`

* `sudo /etc/init.d/nginx restart`
* `cd /home/ubuntu/webapps/genewiki/ & mkdir logs`

* `sudo supervisorctl reread`
* `sudo supervisorctl add genewiki`
* `sudo supervisorctl add genewiki_celery`

* `touch debug.log`
* `chmod 777 debug.log`

* `sudo chown deploy:deploy /bin/gunicorn_start`
* `sudo chmod a+x /bin/gunicorn_start`

* `sudo chmod 777 webapps/genewiki/logs/`
* `import os`
`os.environ['DJANGO_SETTINGS_MODULE'] = 'genewiki.settings'`
* 'python manage.py syncdb'

#### Application

* `sudo supervisorctl restart genewiki_celery`
* `sudo supervisorctl restart genewiki`


### Utils

* Flow diagram of the database relationships
* `python manage.py graph_models -a -o myapp_models.png`
* `celery --app=genewiki.common worker -B -E -l INFO`
* `ssh -i .ssh/path/to/key ubuntu@suv05.scripps.edu`


### Notes



### Known issues:


### Definitions:


