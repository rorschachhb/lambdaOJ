from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView

app = Flask(__name__, static_url_path='/oj/static')
app.config.from_object('config')
admin = Admin(app, url='/oj/admin/')

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

import views, models

admin.add_view(ModelView(models.User, db.session))
admin.add_view(ModelView(models.Problem, db.session))
admin.add_view(ModelView(models.Submit, db.session))
