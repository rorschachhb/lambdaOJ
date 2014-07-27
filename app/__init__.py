from flask import Flask, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.fileadmin import FileAdmin
import os.path as op
import redis
import ldap
import crypt
from config import CSRF_SECRET_KEY

app = Flask(__name__, static_url_path='/oj/static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024
app.config['CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = CSRF_SECRET_KEY

parent_dir = op.split(op.dirname(__file__))[0]
db_dir = op.join(parent_dir, 'db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + op.join(db_dir, 'app.db')
SQLALCHEMY_MIGRATE_REPO = op.join(db_dir, 'db_repository')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_MIGRATE_REPO'] = SQLALCHEMY_MIGRATE_REPO

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

rds = redis.Redis(host='127.0.0.1', port=6379, db=0)

# l = ldap.initialize(LDAP_SERVER)
# l.simple_bind_s(LDAP_BINDDN, LDAP_BINDPW)

people_basedn = 'ou=people,dc=lambda,dc=cool'
groups_basedn = 'ou=groups,dc=lambda,dc=cool'

import views, models

admin = Admin(app, name='lambdaOJ', url='/oj/admin')

path = op.join(op.dirname(__file__), 'static')
admin.add_view(FileAdmin(path, '/static/', name='Static Files'))
admin.add_view(ModelView(models.User, db.session))
admin.add_view(ModelView(models.Problem, db.session))
admin.add_view(ModelView(models.Submit, db.session))
