# Online Judge Web Project

LambdaOJ



## Requirements

Packages:

* python python-pip python-virtualenv
* python-imaging python-devel
* openldap-devel-static
* hiredis hiredis-devel libhiredis0_10
* libmysqld-devel

Services:

* MySQL (you need to create a lambdaoj database in Mysql, too)
* Redis server
* LDAP server
* Web server
* uWSGI



## Installation

Create and activate virtual environment:

```
cd <path/to/lambdaoj>
virtualenv --no-site-packages venv
source venv/bin/activate
```

Install requirements:
(you may need to install other dependencies)

```
pip install -r requirements.txt
```

Copy the example config files, modify them as you need:

```
cp app/config.py.example app/config.py
cp db/config.py.example db/config.py
editor app/config.py
editor db/config.py
```

Create local database:

```
cd db
./db_create.py  
```

Compile core judge program, initialize redis for it:

```
cd judge
make
./init-redis.py
```

If you want syslog from the core judge program, configure your `rsyslog`:
(it will send messages to user.*)

```
sudo editor /etc/rsyslog.conf
```

Initialization uWSGI:
(It will prompt for `user`, `group`, `port` for lambdaOJ Web Process,
and generate `lambdaoj.ini` and `run.sh`.)

```
./init-uwsgi.sh
```

After that, You need to configure Web Server according to port in lambdaoj.ini



## Running

```
<path/to/lambdaoj>/run.sh
```
