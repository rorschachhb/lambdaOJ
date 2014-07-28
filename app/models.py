from app import db

ROLE_USER = 0
ROLE_ADMIN = 1

roles = { ROLE_USER: 'user',
	ROLE_ADMIN: 'admin'
}

STATUS_NORMAL = 0
STATUS_BLOCKED = 1

statuses = { STATUS_NORMAL: 'normal',
	STATUS_BLOCKED: 'blocked'
}

PENDING = 0
TIME_LIMIT_EXCEEDED = 1
MEM_LIMIT_EXCEEDED = 2
WRONG_ANSWER = 3
RUNTIME_ERROR = 4
COMPILE_ERROR = 5
BANNED_SYSCALL = 6
ACCEPTED = 7
OUTPUT_LIMIT_EXCEEDED = 8

oj_states = {
	PENDING: 'Pending...',
	TIME_LIMIT_EXCEEDED: 'Time Limit Exceeded',
	MEM_LIMIT_EXCEEDED: 'Memory Limit Exceeded',
	WRONG_ANSWER: 'Wrong Answer',
	RUNTIME_ERROR: 'Runtime Error',
	COMPILE_ERROR: 'Compilation Error',
	BANNED_SYSCALL: 'Banned Syscall',
	ACCEPTED: 'Accepted',
	OUTPUT_LIMIT_EXCEEDED: 'Output Limit Exceeded'
}

C = 0
CPP = 1

languages = {
	C: 'C',
	CPP: 'C++',
}

class User(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	username = db.Column(db.String(64), index = True, unique = True)
	role = db.Column(db.String(5), default = 'user')
	sid = db.Column(db.String(10))

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
	time_limit = db.Column(db.Integer)
	memory_limit = db.Column(db.Integer)
	description = db.Column(db.Text)
	input_description = db.Column(db.Text)
	output_description = db.Column(db.Text)
	input_sample = db.Column(db.Text)
	output_sample = db.Column(db.Text)
	hint = db.Column(db.Text)
	sample_num = db.Column(db.Integer)

class Submit(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	problem = db.Column(db.Integer, db.ForeignKey('problem.id'))
	user = db.Column(db.Integer, db.ForeignKey('user.id'))
	language = db.Column(db.SmallInteger)
	submit_time = db.Column(db.Float)
	code_file = db.Column(db.Text(500))
