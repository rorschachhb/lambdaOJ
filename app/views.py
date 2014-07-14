from flask import render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm
from forms import LoginForm, EditForm, UploadForm, SignupForm
from models import User, ROLE_USER, ROLE_ADMIN
from datetime import datetime, timedelta
from werkzeug import secure_filename

@app.route('/oj/')
@app.route('/oj/index/')
@login_required
def index():
	pbs=None
	return render_template("index.html",
		pbs=pbs)

@app.route('/oj/login/', methods = ['GET', 'POST'])
def login():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data, password=form.password.data).first()
		if user:
			login_user(user, remember = form.remember_me.data)
			flash('Welcome %s' % user.nickname)
			return redirect(request.args.get('next') or url_for('index'))
		else:
			flash('Wrong name or password!')
	return render_template('login.html',
		form = form)

@app.route('/oj/logout/')
@login_required
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/oj/signup/', methods = ['GET', 'POST'])
def signup():
	if g.user and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = SignupForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user is None:
			user = User(email=form.email.data, password=form.password.data, nickname=form.nickname.data, role=ROLE_USER)
			db.session.add(user)
			db.session.commit()
			flash('Please log in now.')
			return redirect(url_for('login'))
		else:
			flash('This email address has already been registerd, please try another one.')
	return render_template('signup.html',
		form = form)

@app.route('/oj/upload/', methods = ['GET', 'POST'])
@login_required
def upload():
	form = UploadForm()
	return render_template('upload.html',
		form = form)

@app.before_request
def before_request():
	g.user = current_user

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))