from flask import render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm
from forms import LoginForm, EditForm, SubmitForm, SignupForm, PostForm
from models import *
from datetime import datetime, timedelta
from werkzeug import secure_filename
import os
import hashlib
import json
import socket
from shutil import rmtree


PROBLEMS_PER_PAGE = 10
SUBS_PER_PAGE = 10

host = '127.0.0.1'
port = 8787

basedir = os.path.abspath(os.path.dirname(__file__))

@app.route('/', defaults={'page': 1})
@app.route('/oj/', defaults={'page': 1})
@app.route('/oj/index/', defaults={'page': 1})
@app.route('/oj/index/<int:page>')
def index(page):
	print basedir
	pbs = Problem.query.paginate(page, PROBLEMS_PER_PAGE)
	for problem in pbs.items:
		subnum = len(Submit.query.filter_by(problem=problem.id).all())
		acnum = len(Submit.query.filter_by(problem=problem.id, score=1).all())
		if subnum == 0:
                        problem.avg = 0.0
                else:
                        problem.avg = (1000 * acnum / subnum ) / 10.0
	tuser = modify_user(g.user)
	return render_template("index.html",
		pbs=pbs, 
		user = tuser)

@app.route('/oj/login/', methods = ['GET', 'POST'])
def login():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data, password=form.password.data).first()
		if user:
			login_user(user, remember = form.remember_me.data)
			return redirect(request.args.get('next') or url_for('index'))
		else:
			flash('Wrong name or password!')
	tuser = modify_user(g.user)
	return render_template('login.html',
		               form = form, user = tuser)

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
		s.language = languages[s.language]
		user_tmp = User.query.filter_by(id=s.user).first()
		s.user = user_tmp.nickname
		score, sub_results = parse_json(s.results)
		s.score = score
	tuser = modify_user(g.user)
	return render_template('status.html', 
		subs = subs, 
		user = tuser)

@app.route('/oj/submit_info/<int:sid>/', defaults={'page':1})
@app.route('/oj/submit_info/<int:sid>/<int:page>')
@login_required
def submit_info(sid, page):
	if sid is not None:
		sub = Submit.query.filter_by(id=sid).first()
		if sub:
			user = User.query.filter_by(id=sub.user).first()
			if user.id == g.user.id:
				sub.language = languages[sub.language]
				user_tmp = User.query.filter_by(id=sub.user).first()
				sub.user = user_tmp.nickname
				problem = Problem.query.filter_by(id=sub.problem).first()
				tuser = modify_user(g.user)
				score, sub_results = parse_json(sub.results)
				fp = open(sub.code_file, 'r')
				code = fp.read()
				fp.close()
				return render_template('submit_info.html', 
					problem = problem, 
					sub = sub_results, 
					score = score,
					code = code,
					user = tuser)
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
	form.problem_id.choices = [(p.id, p.title) for p in Problem.query.all()]
	if form.validate_on_submit():
		pid = form.problem_id.data
		p = Problem.query.get(pid)
		if p is None:
			flash("Problem %d doesn't exist!" % (pid))
			return redirect(url_for('submit'))
		else:
			#rename
			filename = secure_filename(form.upload_file.data.filename)
			filepath = basedir + '/static/users/%d/%s' % (g.user.id, filename)
			form.upload_file.data.save(filepath)
			hmd5 = hashlib.md5()
			fp = open(filepath,"rb")
			hmd5.update(fp.read())
			filehash = hmd5.hexdigest()
			new_filepath = basedir + '/static/users/%d/%s%s' % (g.user.id, datetime.now(), '_' + filehash + '_' + filename)
			os.rename(filepath, new_filepath)

			if not os.path.exists(basedir + "/static/users/%d/%s" % (g.user.id, filehash)):
				os.mkdir(basedir + "/static/users/%d/%s" % (g.user.id, filehash))

			#request
			request = {
				"code_path": new_filepath,
				"lang_flag": form.language.data,
				"work_dir": basedir + "/static/users/%d/%s/" % (g.user.id, filehash),
				"test_dir": basedir + "/statics/problems/%d/data/" % (pid),
				"test_sample_num": 1,
				"time_limit": p.time_limit,
				"mem_limit": p.memory_limit
			}
			request_json = json.dumps(request)

			#connect socket
			jsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			jsocket.connect((host, port))
			jsocket.send(request_json)
			result_json = jsocket.recv(1024)
			jsocket.close()

			#write database
			score, sub_results = parse_json(result_json)
			time = datetime.now()
			sub = Submit(problem = pid,
				user = g.user.id,
				language = form.language.data,
				score = score,
				results = result_json.decode('utf-8'),
				submit_time = time,
				code_file = new_filepath)
			db.session.add(sub)
			db.session.commit()

			rmtree( basedir + "/static/users/%d/%s/" % (g.user.id, filehash))
			#return something
			s = Submit.query.filter_by(user=g.user.id, submit_time=time).first()
			tuser = modify_user(g.user)
			return redirect(url_for('submit_info', sid = s.id))
	tuser = modify_user(g.user)
	return render_template('submit.html',
                               form = form,
                               pid = pid, 
                               user = tuser)

@app.route('/oj/problem/', defaults={'problem_id':1})
@app.route('/oj/problem/<int:problem_id>')
def problem(problem_id):
	problem = Problem.query.filter_by(id=problem_id).first()
	if problem:
		tuser = modify_user(g.user)
		return render_template('problem.html',
			problem=problem, 
			user = tuser)
	else:
		flash("problem doesn't exit.")
		return redirect(url_for('index'))


@app.route('/oj/signup/', methods = ['GET', 'POST'])
def signup():
	if g.user and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = SignupForm()
	if form.validate_on_submit():
		print form.role.data
		user = User.query.filter_by(email=form.email.data).first()
		if user is None:
			user = User(email=form.email.data, 
				password=form.password.data, 
				nickname=form.nickname.data, 
				role=form.role.data,
				status=STATUS_NORMAL)
			db.session.add(user)
			db.session.commit()
			u = User.query.filter_by(email=user.email).first()
			os.mkdir(basedir + '/static/users/%d' % (u.id))
			flash('Please log in now.')
			return redirect(url_for('login'))
		else:
			flash('This email address has already been registerd, please try another one.')
	tuser = modify_user(g.user)
	return render_template('signup.html',
                               form = form, user = tuser)

@app.before_request
def before_request():
	g.user = current_user

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))

def modify_user(tuser):
        try: 
                tuser.role = roles[tuser.role]
                tuser.status = statuses[tuser.status]
        except AttributeError:
                tuser = None
        return tuser

def parse_json(results_json):
	if len(results_json) > 0:
		if results_json[0] is '{':
			results = json.loads(results_json)
			right = 0
			wrong = 0
			for i in results:
				if results[i] [state] is not 0:
					wrong = wrong + 1
				else:
					right = right + 1
			score = 1.0 * right / (right + wrong)
			return score, results
		elif results_json[0] is '@':
			return 0, 'bad syscall: ' + results_json[1:]
	else:
		return 0, None
