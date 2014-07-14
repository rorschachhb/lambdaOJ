from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask.ext.wtf.recaptcha import RecaptchaField

class LoginForm(Form):
	email = TextField('email', validators = [DataRequired(), Email()])
	password =  PasswordField('password', validators = [DataRequired()])
	remember_me = BooleanField('remember_me', default = False)

class EditForm(Form):	
	password =  PasswordField('password', validators = [DataRequired(), EqualTo('password_confirm', message='Passwords must match')])
	password_confirm =  PasswordField('password_confirm', validators = [DataRequired()])

class UploadForm(Form):
	problem_id = SelectField('problem id:', choices = [('1', 'one'), ('2', 'two'), ('3', 'three')], validators = [DataRequired()])
	upload_file = FileField('image', validators=[FileRequired()])
	recaptcha = RecaptchaField()

class SignupForm(Form):
	email = TextField('email', validators = [DataRequired(), Email()])
	nickname = TextField('nickname', validators = [DataRequired()])
	password =  PasswordField('password', validators = [DataRequired(), EqualTo('password_confirm', message='Passwords must match')])
	password_confirm =  PasswordField('password_confirm', validators = [DataRequired()])
