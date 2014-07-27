import os
basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = "mysql://oj:password@localhost/lambdaoj"
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
