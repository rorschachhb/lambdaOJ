#!venv/bin/python

from app.models import *
from app import db

from random import randint
from datetime import datetime


for i in range(1, 10000):
	s = Submit(problem = (i - 1) / 10 + 1,
		user = 1,
		status = randint(0, 7),
		time = randint(0, 10),
		memory = randint(0, 100),
		language = randint(0, 2),
		submit_time = datetime.utcnow(),
		code_file = 'some certain path',
		error_message = 'some error message')
	db.session.add(s)

db.session.commit()