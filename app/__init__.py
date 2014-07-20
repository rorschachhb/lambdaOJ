from flask import Flask, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.fileadmin import FileAdmin
import os.path as op

app = Flask(__name__, static_url_path='/oj/static')
app.config.from_object('config')

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

import views, models

admin = Admin(app, name='lambdaOJ')

path = op.join(op.dirname(__file__), 'static')
admin.add_view(FileAdmin(path, '/static/', name='Static Files'))

admin.add_view(ModelView(models.User, db.session))
admin.add_view(ModelView(models.Problem, db.session))
admin.add_view(ModelView(models.Submit, db.session))
