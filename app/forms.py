from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask.ext.wtf.recaptcha import RecaptchaField
from models import *

class LoginForm(Form):
	email = TextField('email', validators = [DataRequired(), Email()])
	password =  PasswordField('password', validators = [DataRequired()])
	remember_me = BooleanField('remember_me', default = True)

class EditForm(Form):	
	password =  PasswordField('password', validators = [DataRequired(), EqualTo('password_confirm', message='Passwords must match')])
	password_confirm =  PasswordField('password_confirm', validators = [DataRequired()])

class SubmitForm(Form):
	problem_id = SelectField('problem id:', choices = [(1, 'one'), (2, 'two'), (3, 'three')], validators = [DataRequired()])
	upload_file = FileField('image', validators=[FileRequired()])
	recaptcha = RecaptchaField()

class SignupForm(Form):
	email = TextField('email', validators = [DataRequired(), Email()])
	nickname = TextField('nickname', validators = [DataRequired()])
	password =  PasswordField('password', validators = [DataRequired(), EqualTo('password_confirm', message='Passwords must match')])
	password_confirm =  PasswordField('password_confirm', validators = [DataRequired()])

class PostForm(Form):
	problem_id = IntegerField('problem_id', validators = [DataRequired()])
	title = TextField('title', validators = [DataRequired(), Length(max = 100)])
	time_limit = IntegerField('time_limit', validators = [DataRequired()])
	memory_limit = IntegerField('time_limit', validators = [DataRequired()])
	description = TextAreaField('description', validators = [DataRequired()])
	input_description = TextAreaField('input_description', validators = [DataRequired()])
	output_description = TextAreaField('output_description', validators = [DataRequired()])
	input_sample = TextAreaField('input_sample', validators = [DataRequired()])
	output_sample = TextAreaField('output_sample', validators = [DataRequired()])
	hint = TextAreaField('hint', validators = [Optional()])
