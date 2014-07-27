from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.admin import Admin
import os.path as op
import redis
from config import CSRF_SECRET_KEY, SQLALCHEMY_DATABASE_URI

app = Flask(__name__, static_url_path='/oj/static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024
app.config['CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = CSRF_SECRET_KEY

# parent_dir = op.split(op.dirname(__file__))[0]
# db_dir = op.join(parent_dir, 'db')
# SQLALCHEMY_DATABASE_URI = 'sqlite:///' + op.join(db_dir, 'app.db')
# SQLALCHEMY_MIGRATE_REPO = op.join(db_dir, 'db_repository')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

rds = redis.Redis(host='127.0.0.1', port=6379, db=0)

import views, models

from lambda_admin import *
admin = Admin(app, index_view=lambdaIndexView(name='lambdaOJ', url='/oj/admin'))

path = op.join(op.dirname(__file__), 'static')
admin.add_view(lambdaFileAdmin(path, name='Static Files'))
admin.add_view(lambdaModelView(models.User, db.session))
admin.add_view(lambdaModelView(models.Problem, db.session))
admin.add_view(lambdaModelView(models.Submit, db.session))
