from flask import render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm
from forms import LoginForm, EditForm, SubmitForm, SignupForm, PostForm
from models import *
from datetime import datetime, timedelta
from werkzeug import secure_filename


PROBLEMS_PER_PAGE = 10
SUBS_PER_PAGE = 10

@app.route('/oj/', defaults={'page': 1})
@app.route('/oj/index/', defaults={'page': 1})
@app.route('/oj/index/<int:page>')
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

@app.route('/oj/status/', defaults={'page': 1})
@app.route('/oj/status/<int:page>')
@login_required
def status(page):
	subs = Submit.query.paginate(page, SUBS_PER_PAGE)
	for s in subs.items:
		s.status = results[s.status]
		s.language = results[s.language]
	return render_template('status.html', 
		subs = subs)

@app.route('/oj/submit_info/', defaults={'page':1})
@login_required
def submit_info(sid, page):
	if sid is not None:
		sub = Submit.query.filter_by(id=sid).first()
		if sub:
			user = User.query.filter_by(id=sub.user).first()
			if user.id == g.user.id:
				code_file = sub.code_file
				sub.status = results[s.status]
				sub.language = languages[s.language]
				problem = Problem.query.filter_by(id=sub.problem).first()
				return render_template('submit_info.html', 
					problem = problem, 
					sub = sub,
					code_file = code_file)
			else:
				flash("you don't have access to this submition record.")
		else:
			flash("submition record doesn't exist.")
	return redirect(url_for('status', page=page))

@app.route('/oj/submit/', methods = ['GET', 'POST'])
@app.route('/oj/submit/<int:pid>', methods = ['GET', 'POST'])
@login_required
def submit(pid = None):
	form = SubmitForm()
	if form.validate_on_submit():
                pass
	return render_template('submit.html',
                               form = form, pid = pid)

@app.route('/oj/problem/', defaults={'problem_id':1})
@app.route('/oj/problem/<int:problem_id>')
def problem(problem_id):
	problem = Problem.query.filter_by(problem_id=problem_id).first()
	if problem:
		return render_template('problem.html', problem=problem)
	else:
		flash("problem doesn't exit.")
		return redirect(url_for('index'))


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
				role=ROLE_ADMIN,
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
