from flask import render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm, rds, l, people_basedn, groups_basedn
from forms import LoginForm, EditForm, SubmitForm, PostForm
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
import ldap
import crypt

PROBLEMS_PER_PAGE = 10
SUBS_PER_PAGE = 50

host = '127.0.0.1'
port = 8787

basedir = os.path.abspath(os.path.dirname(__file__))

@app.route('/', defaults={'page': 1})
@app.route('/oj/', defaults={'page': 1})
@app.route('/oj/index/', defaults={'page': 1})
@app.route('/oj/index/<int:page>')
def index(page):
	pbs = Problem.query.paginate(page, PROBLEMS_PER_PAGE)
	return render_template("index.html",
		pbs=pbs, 
		user = g.user)

@app.route('/oj/login/', methods = ['GET', 'POST'])
def login():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		try:
			global l
			l.whoami_s()
		except ldap.LDAPError, e:
			l.unbind_s()
			l = ldap.initialize("ldap://lambda.cool:389")
			l.simple_bind_s('ou=oj, ou=services, dc=lambda, dc=cool', 'aoeirtnsqwertoj')
		user_ldap = l.search_s(people_basedn, ldap.SCOPE_ONELEVEL, '(uid=%s)' % (form.username.data), None)
		if user_ldap: # if user exists
			passwd_list = user_ldap[0][1]['userPassword'][0].split('$')
			if '{CRYPT}' + crypt.crypt(form.password.data, '$' + passwd_list[1] + '$' + passwd_list[2] + '$') == user_ldap[0][1]['userPassword'][0]: # if passwd is right
				print 'password is right'
				user_sql = User.query.filter_by(username=user_ldap[0][1]['uid'][0]).first()
				if l.search_s(groups_basedn, ldap.SCOPE_ONELEVEL, '(&(cn=admin)(member=uid=%s, ou=people, dc=lambda, dc=cool))' % (user_ldap[0][1]['uid'][0]), None):
					role = 'admin'
				else:
					role = 'user'
				try:
					sid = user_ldap[0][1]['employeeNumber'][0]
				except KeyError:
					sid = None
				if user_sql is None: # if user is not in sql database, create one
					user = User(username=user_ldap[0][1]['uid'][0],
						role=role,
						sid=sid)
					db.session.add(user)
					db.session.commit()
					user_sql = User.query.filter_by(username=user_ldap[0][1]['uid'][0]).first()
				else: # if user is already in sql database, overwrite it
					user_sql.role = role
					user_sql.sid = sid
					db.session.commit()
				login_user(user_sql, remember = form.remember_me.data) # login user
				return redirect(request.args.get('next') or url_for('index'))
			else: # if passwd is wrong
				flash('Wrong name or password!')
		else: # if user doesn't exist
			flash('Wrong name or password!')
	return render_template('login.html',
		               form = form, user = g.user)

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
		s.user = user_tmp.username
		status_tmp = rds.hget('lambda:%d:head' % (s.id), 'state')
		if status_tmp is None:
			s.status = 'Pending'
		else:
			s.status = status_tmp
	return render_template('status.html', 
		subs = subs, 
		user = g.user)

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
				sub.user = user.username
				problem = Problem.query.filter_by(id=sub.problem).first()
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
					user = g.user)
	return redirect(url_for('status', page=page))

@app.route('/oj/submit/', methods = ['GET', 'POST'])
@app.route('/oj/submit/<int:pid>', methods = ['GET', 'POST'])
@login_required
def submit(pid = None):
	form = SubmitForm()
	form.problem_id.choices = [(p.id, p.title) for p in Problem.query.all()]
	if request.method == 'POST':
		if os.path.isfile(os.path.join(basedir, 'static/tmp/%s.gif' % (form.validate_code_hash.data))):
			os.remove(os.path.join(basedir, 'static/tmp/%s.gif' % (form.validate_code_hash.data)))
		if form.validate_on_submit():
			pid = form.problem_id.data
			p = Problem.query.get(pid)
			if p is None:
				flash("Problem %d doesn't exist!" % (pid))
				return redirect(url_for('submit'))
			else:
				#rename
				filename = secure_filename(form.upload_file.data.filename)
				filepath = os.path.join(basedir, 'users/%s/%s' % (g.user.username, filename))
				if not os.path.exists(os.path.join(basedir, 'users/%s/' % (g.user.username))):
					os.makedirs(os.path.join(basedir, 'users/%s/' % (g.user.username)))
				form.upload_file.data.save(filepath)
				hmd5 = hashlib.md5()
				fp = open(filepath,"rb")
				hmd5.update(fp.read())
				filehash = hmd5.hexdigest()
				new_filepath = os.path.join(basedir, 'users/%s/%s%s' % (g.user.username, datetime.now().strftime('%Y-%m-%d-%H:%M:%S'), '_' + filehash + '_' + filename))
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
	vimg.save(os.path.join(basedir, 'static/tmp/%s.gif' % (vhash)), "GIF")
	form.validate_code_hash.data = vhash
	return render_template('submit.html',
                               form = form,
                               validate_img = vhash,
                               pid = pid, 
                               user = g.user)

@app.route('/oj/problem/', defaults={'problem_id':1})
@app.route('/oj/problem/<int:problem_id>')
def problem(problem_id):
	problem = Problem.query.filter_by(id=problem_id).first()
	if problem:
		return render_template('problem.html',
			problem=problem, 
			user = g.user)
	else:
		return redirect(url_for('index'))

@app.route('/oj/profile/', defaults={'page': 1})
@login_required
def profile(page):
	try:
		global l
		l.whoami_s()
	except ldap.LDAPError, e:
		l.unbind_s()
		l = ldap.initialize("ldap://lambda.cool:389")
		l.simple_bind_s('ou=oj, ou=services, dc=lambda, dc=cool', 'aoeirtnsqwertoj')
	user_attrs = l.search_s(people_basedn, ldap.SCOPE_ONELEVEL, '(uid=%s)' % (g.user.username), None)

	subs = Submit.query.filter_by(user=g.user.id).order_by(Submit.submit_time).paginate(page, SUBS_PER_PAGE)
	for s in subs.items:
		s.language = languages[s.language]
		status_tmp = rds.hget('lambda:%d:head' % (s.id), 'state')
		if status_tmp is None:
			s.status = 'Pending'
		else:
			s.status = status_tmp

	return render_template('profile.html', 
		user_attrs = user_attrs[0][1],
		user = g.user, 
		subs = subs)

@app.route('/oj/passwd/')
@fresh_login_required
def passwd():
        pass

@app.errorhandler(413)
def request_entity_too_large(e):
	# return render_template('413.html'), 413
	flash('Object file too large.')
	return redirect(url_for('submit'))

@app.before_request
def before_request():
	g.user = current_user

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))

def judge_on_commit(mapper, connection, model):
	#write redis
	rds.hset('lambda:%d:head' % (model.id), 'state', 'Pending')

	#create work dir
	filepath = model.code_file
	hmd5 = hashlib.md5()
	fp = open(filepath,"rb")
	hmd5.update(fp.read())
	filehash = hmd5.hexdigest()
	u = User.query.get(model.user)
	if not os.path.exists(os.path.join(basedir, "users/%s/%s" % (u.username, filehash))):
		os.makedirs(os.path.join(basedir, "users/%s/%s" % (u.username, filehash)))
	#request
	pid = model.problem
	p = Problem.query.get(pid)
	json_req = {"submit_id": model.id,
	            "code_path": model.code_file,
	            "test_sample_num": p.sample_num,
	            "lang_flag": model.language,
	            "work_dir": os.path.join(basedir, "users/%s/%s/" % (u.username, filehash)),
	            "test_dir": os.path.join(basedir, "problems/%d/data/" % (pid)),
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
# event.listen(Submit, 'after_insert', judge_on_commit)
