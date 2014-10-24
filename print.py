import hashlib

from flask import Flask, render_template, redirect, url_for, request, g, flash
from userdb import User, Group, AccessEntry, AccessToken, DBError, NoSuchEntity
from sessiondb import Session
import conf
import os

app = Flask('print')
app.debug = True

# Runs a function with a response after the response has been generated
def add_after_request(f):
	if not hasattr(g, 'after_request'):
		g.after_request=[]
	g.after_request.append(f)
	return f

# Runs the response	
@app.after_request 
def do_after_request(resp):
	for f in getattr(g, 'after_request', []):
		f(resp)
	g.after_request=[]
	return resp

# Generates a message that will be shown to user
def flash(msg, cat):
	if not hasattr(g, 'flashes'):
		g.flashes=[]
	g.flashes.append((msg, cat))

# Gets User and Session objects for a given request
def get_user_session(request):
	sid = request.cookies.get('session')
	try:
		sid = int(sid)
	except (ValueError, TypeError):
		sid = None
	if sid:
		try:
			sess = Session.FromID(sid)
		except DBError:
			sid = None
	if not sid:
		sess = Session.Create(User.NOBODY)
		add_after_request(lambda resp: resp.set_cookie('session', str(sess.id)))
	user=sess.User()
	return user, sess

# 
@app.before_request
def do_get_user_session():
	g.user, g.session = get_user_session(request)

@app.before_request
def do_set_global_conf():
	g.conf = conf

@app.route('/')
def index():
	return redirect(url_for('print_main'))
	
@app.route('/print/')
def print_main():
	return render_template('print_main.html', operations=[['Log In/Out', url_for('loginout')],
														  ['Register', url_for('register')],
														  ['Print File', url_for('print_file')],
														  ['Print a test page', url_for('test1')],
														  ['Test operation 2', url_for('test2')]])

@app.route('/print/op/null/')
def null():
	return render_template('op_null.html')
	
@app.route('/print/op/loginout/', methods=['GET', 'POST'])
def loginout():
	if g.user.id == User.NOBODY.id:
		return redirect(url_for('login'))
	else:
		return redirect(url_for('logout'))

@app.route('/print/op/login/', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		try:
			newuser = User.FromName(request.form['username'])
			pwdhash = hashlib.sha512(request.form['password']).hexdigest()
		except KeyError:
			flash('Bad request', 'error')
		except DBError:
			flash('Invalid username (did you <a href="%s">register</a>?)'%(url_for('register')), 'error')
		else:
			if newuser.password == pwdhash:
				g.user = newuser
				g.session.uid = g.user.id
				g.session.Update()
				flash('Logged in as %s'%(newuser.username), 'success')
			else:
				flash('Invalid password', 'error')
	return render_template('op_login.html')

@app.route('/print/op/logout/', methods=['GET', 'POST'])
def logout():
	if request.method == 'POST':
		g.session.uid = User.NOBODY.id
		g.session.Update()
		flash('Logged out', 'success')
	return render_template('op_logout.html')
	
@app.route('/print/op/register/', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		try:
			username = request.form['username']
			password = request.form['password']
			email = request.form['email']
		except KeyError:
			flash('Bad request', 'error')
		else:
			try:
				user = User.FromName(username)
			except NoSuchEntity:
				newuser = User.Create(username, hashlib.sha512(password).hexdigest(), email, conf.DEFAULT_BALANCE)
				flash('Created account %s'%(newuser.username), 'success')
			else:
				flash('User already exists', 'error')
	return render_template('op_register.html')
			

@app.route('/print/op/test1/')
def test1():
	os.system('lp -U %s /home/vaillap/test.txt'%g.user.username) 
	return 'You just printed a test page!  How do you feel about yourself?'

@app.route('/print/op/print/', methods=['GET', 'POST'])
def print_file():
	if request.method == 'POST':
		rfile = request.files['file']
		if rfile.filename.rpartition('.')[2] not in conf.ALLOWED_EXTENSIONS:
			flash('Bad file extension (consider printing to PDF)', 'error')
		else:
			fname = os.tmpnam()
			request.files['file'].save(fname)
			os.system('lp -U "%s" %s'%(g.user.username, fname))
			os.unlink(fname)
			flash('Printed successfully', 'success')
	return render_template('op_print.html')
	
@app.route('/print/op/test2/')
def test2():
	return 'Hello from test2!'
