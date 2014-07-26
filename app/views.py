from flask import render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm, rds
from forms import LoginForm, EditForm, SubmitForm, SignupForm, PostForm
from models import *
from werkzeug import secure_filename
import os
import hashlib
import json
import socket
from shutil import rmtree
from sqlalchemy import event
from app import validate_code
from time import time
from datetime import datetime


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
	pbs = Problem.query.paginate(page, PROBLEMS_PER_PAGE)
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
	subs = Submit.query.order_by(Submit.submit_time).paginate(page, SUBS_PER_PAGE)
	for s in subs.items:
		s.language = languages[s.language]
		user_tmp = User.query.filter_by(id=s.user).first()
		s.user = user_tmp.nickname
		status_tmp = rds.hget('lambda:%d:head' % (s.id), 'state')
		if status_tmp is None:
			s.status = 'Pending'
		else:
			s.status = status_tmp
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
			if ( user.id == g.user.id ) or ( g.user.role is ROLE_ADMIN ):
				sub.language = languages[sub.language]
				sub.user = user.nickname
				problem = Problem.query.filter_by(id=sub.problem).first()
				tuser = modify_user(g.user)
				fp = open(sub.code_file, 'r')
				code = fp.read()
				fp.close()
				error_message = None
				status = rds.hget('lambda:%d:head' % (sub.id), 'state')
				if status is None:
					status = 'Pending'
				if status == 'Pending':
					sub_results = status
				elif status == 'Compilation Error':
					sub_results = status
					error_message = rds.hget('lambda:%d:head' % (sub.id), 'err_message')
				else:
					sub_results = []
					for i in range(0, problem.sample_num):
						sub_results.append(rds.hgetall('lambda:%d:result:%d' % (sub.id, i)))
				return render_template('submit_info.html', 
					problem = problem, 
					sub = sub,
					sub_results = sub_results, 
					error_message = error_message,
					code = code,
					user = tuser)
	return redirect(url_for('status', page=page))

ALLOWED_EXTENSIONS = set(['c', 'C', 'cpp', 'CPP', 'py'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/oj/submit/', methods = ['GET', 'POST'])
@app.route('/oj/submit/<int:pid>', methods = ['GET', 'POST'])
@login_required
def submit(pid = None):
	form = SubmitForm()
	form.problem_id.choices = [(p.id, p.title) for p in Problem.query.all()]
	if request.method == 'POST':
		if os.path.isfile(basedir + '/static/tmp/%s.gif' % (form.validate_code_ans.data)):
			os.remove(basedir + '/static/tmp/%s.gif' % (form.validate_code_ans.data))
		if form.validate_on_submit():
			pid = form.problem_id.data
			p = Problem.query.get(pid)
			if p is None:
				flash("Problem %d doesn't exist!" % (pid))
				return redirect(url_for('submit'))
			else:
				hmd5 = hashlib.md5()
				hmd5.update(form.validate_code.data)
				vhash = hmd5.hexdigest()
				if vhash != form.validate_code_ans.data:
					flash("Validate code incorrect!")
					return redirect(url_for('submit'))
				else:
					#rename
					filename = secure_filename(form.upload_file.data.filename)
					filepath = basedir + '/users/%d/%s' % (g.user.id, filename)
					form.upload_file.data.save(filepath)
					hmd5 = hashlib.md5()
					fp = open(filepath,"rb")
					hmd5.update(fp.read())
					filehash = hmd5.hexdigest()
					new_filepath = basedir + '/users/%d/%s%s' % (g.user.id, datetime.now().strftime('%Y-%m-%d-%H:%M:%S'), '_' + filehash + '_' + filename)
					os.rename(filepath, new_filepath)

					#write database
					timenow = -1.0 * time()
					sub = Submit(problem = pid,
						user = g.user.id,
						language = form.language.data,
						submit_time = timenow,
						code_file = new_filepath)
					db.session.add(sub)
					db.session.commit()

					#return something
					s = Submit.query.filter_by(user=g.user.id, submit_time=timenow).first()
					return redirect(url_for('submit_info', sid = s.id))
	vimg, vstr = validate_code.create_validate_code(font_type="app/static/fonts/SourceCodePro-Bold.otf")
	hmd5 = hashlib.md5()
	hmd5.update(vstr)
	vhash = hmd5.hexdigest()
	vimg.save(basedir + '/static/tmp/%s.gif' % (vhash), "GIF")
	form.validate_code_ans.data = vhash
	tuser = modify_user(g.user)
	return render_template('submit.html',
                               form = form,
                               validate_img = vhash,
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
				role=form.role.data,
				status=STATUS_NORMAL)
			db.session.add(user)
			db.session.commit()
			u = User.query.filter_by(email=user.email).first()
			if not os.path.exists(basedir + '/users/%d' % (u.id)):
				os.makedirs(basedir + '/users/%d' % (u.id))
			flash('Please log in now.')
			return redirect(url_for('login'))
		else:
			flash('This email address has already been registerd, please try another one.')
	tuser = modify_user(g.user)
	return render_template('signup.html',
                               form = form, user = tuser)

@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

@app.errorhandler(413)
def request_entity_too_large(e):
	# return render_template('413.html'), 413
	flash('Object file too large.')
	return redirect(url_for('submit')), 413

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
			for r in results:
				if r.state is not 0:
					wrong = wrong + 1
				else:
					right = right + 1
				r.state = oj_states[r.state]
			score = 1.0 * right / (right + wrong)
			return score, results
		elif results_json[0] is '@':
			return 0, 'bad syscall: ' + results_json[1:]
		else:
			return 0, results_json
	else:
		return 0, None

def judge_on_commit(model):
	#write redis
	rds.hset('lambda:%d:head' % (model.id), 'state', 'Pending')

	#create work dir
	filepath = model.code_file
	hmd5 = hashlib.md5()
	fp = open(filepath,"rb")
	hmd5.update(fp.read())
	filehash = hmd5.hexdigest()
	user_id = model.user
	if not os.path.exists(basedir + "/users/%d/%s" % (user_id, filehash)):
		os.makedirs(basedir + "/users/%d/%s" % (user_id, filehash))
	#request
	pid = model.problem
	p = Problem.query.get(pid)
	json_req = {"submit_id": model.id,
	            "code_path": model.code_file,
	            "test_sample_num": p.sample_num,
	            "lang_flag": model.language,
	            "work_dir": basedir + "/users/%d/%s/" % (user_id, filehash),
	            "test_dir": basedir + "/problems/%d/data/" % (pid),
	            "time_limit": [p.time_limit]*p.sample_num,
	            "mem_limit": [p.memory_limit]*p.sample_num}
	request_json = json.dumps(json_req)

	#connect socket
	jsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	jsocket.connect((host, port))
	jsocket.send(request_json)
	jsocket.close()

	#remove work dir
	#rmtree( basedir + "/users/%d/%s/" % (g.user.id, filehash))
#event.listen(Submit, 'after_insert', judge_on_commit)
