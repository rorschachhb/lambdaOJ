#!venv/bin/python

from app.models import *
from app import db

for i in range(1, 1000):
	p = Problem(problem_id=i, 
		title='title', 
		time_limit=10, 
		memory_limit=100, 
		description='description', 
		input_description='input description', 
		output_description='output description', 
		input_sample='input sample', 
		output_sample='output sample', 
		hint='hint')
	db.session.add(p)

db.session.commit()