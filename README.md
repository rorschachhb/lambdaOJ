# Online Judge Web Project

LambdaOJ



## Requirements

Basic Requirements:

* python
* python-pip
* python-virtualenv

To start from uWSGI, you need to have it installed:

```
sudo pip install uwsgi
```



## Installation

First, install build requirements,
```
sudo apt-get build-dep python-imaging
sudo apt-get install python-dev
```

For Ubuntu users, make sure that PIL's setup.py can find JPEG/ZLIB, by creating find-able links to the libraries,

for Ubuntu x64:
```
sudo ln -s /usr/lib/i386-linux-gnu/libfreetype.so /usr/lib/

sudo ln -s /usr/lib/i386-linux-gnu/libz.so /usr/lib/

sudo ln -s /usr/lib/i386-linux-gnu/libjpeg.so /usr/lib/
```

for Ubuntu x86:
```
sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib/

sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib/

sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib/
```

 Second, `cd` into the `lambdaOJ` directory,
create and activate virtual environment:

```
virtualenv --no-site-packages venv
source venv/bin/activate
```

Then, install requirements:

```
pip install -r requirements.txt
```

Create local database
```
./db_create.py  
./db_migrate.py
```



## Testing

Make sure you have activated the virtual environment:

```
source venv/bin/activate
```

Run it (without a web server):

```
./lambdaoj.py
```

It will listen on `127.0.0.1:5000` by default.
	


## uWSGI

Initialization:

```
./init-uwsgi.sh
```

It will prompt for `user`, `group`, `port` for lambdaOJ Web Process,
and generate `lambdaoj.ini` and `run.sh`.

After that, you can execute `run.sh` to run from uWSGI each time.

Of course, for actual use,
you also need to configure your web server.
