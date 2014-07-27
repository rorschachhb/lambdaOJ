from flask import url_for, redirect, flash
from flask.ext.login import current_user
from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.base import AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.fileadmin import FileAdmin
import ldap
from config import LDAP_SERVER, LDAP_BINDDN, LDAP_BINDPW, groups_basedn

def is_admin():
	l = ldap.initialize(LDAP_SERVER)
	l.simple_bind_s(LDAP_BINDDN, LDAP_BINDPW)
	if l.search_s(groups_basedn, ldap.SCOPE_ONELEVEL, '(&(cn=admin)(member=uid=%s, ou=people, dc=lambda, dc=cool))' % (current_user.username), None):
		return True
	else:
		return False

class lambdaIndexView(AdminIndexView):
	def __init__(self,
		name=None,
		category=None,
		endpoint=None,
		url=None,
		template='admin/index.html'):
		super(lambdaIndexView, self).__init__(name=name,
			category=category,
			endpoint=endpoint,
			url=url,
			template=template)
	@expose('/')
	def index(self):
		if current_user.is_authenticated():
			if is_admin():
				return self.render(self._template)
			else:
				flash('You have no access to admin view.')
				return redirect(url_for('index'))
		else:
			flash('Please login before accessing admin view.')
			return redirect(url_for('login'))



class lambdaFileAdmin(FileAdmin):
	def __init__(self, path, name, **kwargs):
		# You can pass name and other parameters if you want to
		super(lambdaFileAdmin, self).__init__(path, name=name, **kwargs)

	def is_accessible(self):
		return current_user.is_authenticated() and is_admin()
		

class lambdaModelView(ModelView):
	def __init__(self, model, session, **kwargs):
		# You can pass name and other parameters if you want to
		super(lambdaModelView, self).__init__(model, session, **kwargs)

	def is_accessible(self):
		return current_user.is_authenticated() and is_admin()