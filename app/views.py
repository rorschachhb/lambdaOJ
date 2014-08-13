from flask import jsonify, render_template, flash, redirect, session, url_for, request, g 
from flask.ext.login import login_user, logout_user, current_user, login_required, login_fresh, confirm_login, fresh_login_required
from app import app, db, lm, rds
from forms import LoginForm, EditForm, SubmitForm, Form
from models import *
from werkzeug import secure_filename
import os
import hashlib
import json
import socket
from shutil import rmtree
from sqlalchemy import event
from time import time
from datetime import datetime
import ldap
import ldap.modlist as modlist
import crypt
import random
import string
from config import LDAP_BINDDN, LDAP_BINDPW, LDAP_SERVER, people_basedn, groups_basedn
from sqlalchemy import desc

PROBLEMS_PER_PAGE = 10
SUBS_PER_PAGE = 100

host = '127.0.0.1'
port = 8787

basedir = os.path.abspath(os.path.dirname(__file__))

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
	if form.validate_on_submit() and check_qaptcha():
		l = ldap.initialize(LDAP_SERVER)
		l.simple_bind_s(LDAP_BINDDN, LDAP_BINDPW)
		user_ldap = l.search_s(people_basedn, ldap.SCOPE_ONELEVEL, '(uid=%s)' % (form.username.data), None)
		if user_ldap: # if user exists
			passwd_list = user_ldap[0][1]['userPassword'][0].split('$')
			if '{CRYPT}' + crypt.crypt(form.password.data, '$' + passwd_list[1] + '$' + passwd_list[2] + '$') == user_ldap[0][1]['userPassword'][0]: # if passwd is right
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
				l.unbind_s()
				return redirect(request.args.get('next') or url_for('index'))
			else: # if passwd is wrong
				flash('Wrong name or password!')
		else: # if user doesn't exist
			flash('Wrong name or password!')
		l.unbind_s()
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
	subs = Submit.query.order_by(desc(Submit.id)).paginate(page, SUBS_PER_PAGE)
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
			if ( user.id == g.user.id ) or ( g.user.role == 'admin' ):
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
	if request.method == 'POST':
		if form.validate_on_submit() and check_qaptcha():
			pid = form.problem_id.data
			p = Problem.query.get(pid)
			if p is None:
				flash("Problem %d doesn't exist!" % (pid))
				return redirect(url_for('submit'))
			else:
				try:
					languages[form.language.data]
				except KeyError:
					flash('Language not allowed!')
					return redirect(url_for('submit'))
				#rename
				filename = secure_filename(form.upload_file.data.filename)
				filepath = os.path.join(basedir, 'users/%s/%s' % (g.user.username, filename))
				if not os.path.exists(os.path.join(basedir, 'users/%s/' % (g.user.username))):
					os.makedirs(os.path.join(basedir, 'users/%s/' % (g.user.username)))
				form.upload_file.data.save(filepath)
				hmd5 = hashlib.md5()
				fp = open(filepath,"rb")
				hmd5.update(fp.read())
				fp.close()
				filehash = hmd5.hexdigest()
				new_filepath = os.path.join(basedir, 'users/%s/%s%s' % (g.user.username, datetime.now().strftime('%Y-%m-%d-%H:%M:%S'), '_' + filehash + '_' + filename))
				os.rename(filepath, new_filepath)

				#write database
				sub = Submit(problem = pid,
					user = g.user.id,
					language = form.language.data,
					submit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					code_file = new_filepath)
				db.session.add(sub)
				db.session.commit()

                                return redirect(url_for('status'))
	return render_template('submit.html',
                               form = form,
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
	subs = Submit.query.filter_by(user=g.user.id).order_by(desc(Submit.id)).paginate(page, SUBS_PER_PAGE)
	for s in subs.items:
		s.language = languages[s.language]
		status_tmp = rds.hget('lambda:%d:head' % (s.id), 'state')
		if status_tmp is None:
			s.status = 'Pending'
		else:
			s.status = status_tmp

	return render_template('profile.html', 
		user = g.user, 
		subs = subs)

@app.route('/oj/passwd/', methods = ['GET', 'POST'])
@login_required
def passwd():
	form = EditForm()
	if form.validate_on_submit() and check_qaptcha():
		l = ldap.initialize(LDAP_SERVER)
		l.simple_bind_s(LDAP_BINDDN, LDAP_BINDPW)
		[(dn, attrs)] = l.search_s(people_basedn, ldap.SCOPE_ONELEVEL, '(uid=%s)' % (g.user.username), None)
		if dn: # if user exists
			passwd_list = attrs['userPassword'][0].split('$')
			if '{CRYPT}' + crypt.crypt(form.old_password.data, '$' + passwd_list[1] + '$' + passwd_list[2] + '$') == attrs['userPassword'][0]: # if passwd is right
				old = {'userPassword': attrs['userPassword']}
				new = {'userPassword': ['{CRYPT}' + crypt.crypt(form.new_password.data, '$6$%s$'%(''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(10)])))]}
				ldif = modlist.modifyModlist(old, new)
				l.modify_s(dn, ldif)
				logout_user()
				flash('Your password has been reset, please login now.')
				l.unbind_s()
				return redirect(url_for('login'))
			else: # if passwd is wrong
				flash('Password incorrect!')
				l.unbind_s()
				return render_template('passwd.html',
						form = form,
						user = g.user)
		else:
			flash("User doesn't exist, please login again.")
			l.unbind_s()
			return redirect(url_for('login'))
	return render_template('passwd.html',
			form = form,
			user = g.user)

@app.route('/oj/qaptcha/key', methods = ['GET', 'POST'])
def qaptcha_getkey():
	response = {}
	response["error"] = False
	try:
		session["qaptcha_key"] = False
		if request.form["action"] == "qaptcha":
			session["qaptcha_key"] = request.form["qaptcha_key"]
			return jsonify(**response)
		else:
			response["error"] = True
			return jsonify(**response)
	except KeyError:
		response["error"] = True
		return jsonify(**response)

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


def check_qaptcha():
	try:
		k = session["qaptcha_key"]
		if (request.form[str(k)]):
			# it should be empty
			return False
		else:
			session["qaptcha_key"] = False
			return True
	except KeyError:
		return False



def judge_on_commit(mapper, connection, model):
	#write redis
	rds.hset('lambda:%d:head' % (model.id), 'state', 'Pending')

	#create work dir
	filepath = model.code_file
	hmd5 = hashlib.md5()
	fp = open(filepath,"rb")
	hmd5.update(fp.read())
	fp.close()
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
event.listen(Submit, 'after_insert', judge_on_commit)
