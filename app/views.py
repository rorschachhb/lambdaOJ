from app import app

@app.route('/oj/')
@app.route('/oj/index')
def index():
	return "Hello, World!"
