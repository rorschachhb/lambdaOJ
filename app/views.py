from flask import render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm
from forms import LoginForm, EditForm, UploadForm, SignupForm, PostForm
from models import *
from datetime import datetime, timedelta
from werkzeug import secure_filename


PROBLEMS_PER_PAGE = 1

@app.route('/oj/')
@app.route('/oj/index/', defaults={'page': 1})
@app.route('/oj/index/<int:page>')
@login_required
def index(page):
	pbs = Problem.query.paginate(page, PROBLEMS_PER_PAGE)
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

@app.route('/oj/status/')
@login_required
def status():
	subs = None
	render_template('status.html', 
		subs = subs)

@app.route('/oj/submit_info/')
@login_required
def submit_info():
	problem = None
	sub = None
	code_file = None
	render_template('submit_info.html', 
		problem = problem, 
		sub = sub,
		code_file = code_file)

@app.route('/oj/upload/', methods = ['GET', 'POST'])
@login_required
def upload():
	form = UploadForm()
	return render_template('upload.html',
		form = form)

@app.route('/oj/signup/', methods = ['GET', 'POST'])
def signup():
	if g.user and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = SignupForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user is None:
			user = User(email=form.email.data, 
				password=form.password.data, 
				nickname=form.nickname.data, 
				role=form.role.data,
				status=STATUS_NORMAL)
			db.session.add(user)
			db.session.commit()
			flash('Please log in now.')
			return redirect(url_for('login'))
		else:
			flash('This email address has already been registerd, please try another one.')
	return render_template('signup.html',
		form = form)

@app.route('/oj/post/', methods = ['GET', 'POST'])
@login_required
def post():
	if g.user and g.user.role is ROLE_ADMIN:
		form = PostForm()
		if form.validate_on_submit():
			p = Problem.query.filter_by(problem_id=form.problem_id.data).first()
			if p is None:
				p = Problem(problem_id=form.problem_id.data, 
					title=form.title.data, 
					time_limit=form.time_limit.data,
					memory_limit=form.time_limit.data,
					description=form.description.data,
					input_description=form.input_description.data,
					output_description=form.output_description.data,
					input_sample=form.input_sample.data,
					output_sample=form.output_sample.data,
					hint=form.hint.data)
				db.session.add(p)
				db.session.commit()
				flash('problem posted.')
				return redirect(url_for('index'))
			else:
				flash('problem_id is occupied, please try another one.')
	else:
		flash('Only admin can post problems.')
		return redirect(url_for('index'))
	return render_template('post.html', form = form)

@app.before_request
def before_request():
	g.user = current_user

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))