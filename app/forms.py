from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, SelectField, IntegerField, TextAreaField
from wtforms.validators import InputRequired, Length, Email, EqualTo, Optional, NumberRange, ValidationError
from flask_wtf.file import FileField, FileRequired, FileAllowed
from models import *
import hashlib

class LoginForm(Form):
	username = TextField('username', validators = [InputRequired()])
	password =  PasswordField('password', validators = [InputRequired()])
	remember_me = BooleanField('remember_me', default = True)

class EditForm(Form):	
	old_password = PasswordField('old_password', validators = [InputRequired()])
	new_password =  PasswordField('new_password', validators = [InputRequired()])
	confirm_password =  PasswordField('confirm_password', validators = [InputRequired(), EqualTo(fieldname='new_password', message='Password must match!')])

class Captcha(object):
	def __init__(self, fieldname, message=None):
		self.fieldname = fieldname
		self.message = message

	def __call__(self, form, field):
		try:
			other = form[self.fieldname]
		except KeyError:
			raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)
		hmd5 = hashlib.md5()
		hmd5.update(field.data)
		vhash = hmd5.hexdigest()
		if vhash != other.data:
			raise ValidationError('Validate code incorrect!')

class SubmitForm(Form):
	problem_id = IntegerField('problem_id', validators = [InputRequired(), NumberRange(min=1)])
	language = SelectField('language', choices = [(C, 'C'), (CPP, 'C++'), (PYTHON, 'Python')], validators = [InputRequired()], coerce=int)
	upload_file = FileField('upload_file', validators = [FileRequired(), FileAllowed(['c', 'C', 'cpp', 'CPP', 'py'], 'C/C++ and Python codes only!')])
	validate_code = TextField('validate_code', validators = [InputRequired(), Captcha(fieldname='validate_code_hash')])
	validate_code_hash = TextField('validate_code_ans')
