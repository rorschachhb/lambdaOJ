from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, RadioField, IntegerField, TextAreaField
from wtforms.validators import InputRequired, Length, Email, EqualTo, Optional, NumberRange, ValidationError
from flask_wtf.file import FileField, FileRequired, FileAllowed
from models import *
import hashlib


class LoginForm(Form):
	username = TextField('username', validators = [InputRequired()])
	password =  PasswordField('password', validators = [InputRequired()])
	remember_me = BooleanField('remember_me', default = False)

class EditForm(Form):	
	old_password = PasswordField('old_password', validators = [InputRequired()])
	new_password =  PasswordField('new_password', validators = [InputRequired()])
	confirm_password =  PasswordField('confirm_password', validators = [InputRequired(), EqualTo(fieldname='new_password', message='Password must match!')])

class SubmitForm(Form):
	problem_id = IntegerField('problem_id', validators = [InputRequired(), NumberRange(min=1)])
	language = RadioField('language',
                               choices = [(C, 'C'), (CPP, 'C++')],
                               validators = [InputRequired()], coerce=int)
	upload_file = FileField('upload_file', validators = [FileRequired()])
