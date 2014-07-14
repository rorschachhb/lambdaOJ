from app import db

ROLE_USER = 0
ROLE_ADMIN = 1

STATUS_NORMAL = 0
STATUS_BLOCKED = 1

ACCEPTED = 0
TIME_LIMIT_EXCEEDED = 1
MEM_LIMIT_EXCEEDED = 2
WRONG_ANSWER = 3
RUNTIME_ERROR = 4
COMPILE_ERROR = 5
PRESENTATION_ERROR = 6
OUTPUT_LIMIT_EXCEEDED = 7

C = 0
CPP = 1
PYTHON = 2

class User(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	nickname = db.Column(db.String(64), index = True, unique = True)
	email = db.Column(db.String(120), index = True, unique = True)
	password = db.Column(db.String(120))
	role = db.Column(db.SmallInteger, default = ROLE_USER)
	status = db.Column(db.SmallInteger, default = STATUS_NORMAL)
	last_seen = db.Column(db.DateTime)
	last_submition = db.Column(db.DateTime)

	def is_authenticated(self):
		return True

	def is_active(self):
		return True

	def is_anonymous(self):
		return False

	def get_id(self):
		return unicode(self.id)

	def __repr__(self):
		return '<User %r>' % (self.nickname)

class Problem(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	title = db.Column(db.String(100))
	time = db.Column(db.Integer)
	memory = db.Column(db.Integer)
	description = db.Column(db.String(100))
	input_description = db.Column(db.String(100))
	output_description = db.Column(db.String(100))
	sample = db.Column(db.String(100))
	hint = db.Column(db.String(100))

class Submit(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	problem = db.Column(db.Integer, db.ForeignKey('Problem.id'))
	user = db.Column(db.Integer, db.ForeignKey('User.id'))
	status = db.Column(db.SmallInteger)
	time = db.Column(db.Integer)
	memory = db.Column(db.Integer)
	language = db.Column(db.SmallInteger)
	submit_time = db.Column(db.DateTime)
	code = db.Column(db.String(100))
	error_message = db.Column(db.String(100))
