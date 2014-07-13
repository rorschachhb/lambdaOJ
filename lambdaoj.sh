#!/usr/bin/env bash

cd ~prajnamort/hack/lambdaOJ/

source venv/bin/activate
uwsgi --ini lambdaoj.ini
