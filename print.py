import hashlib
import smtplib
import base64
#import urllib

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

# Validates email submitted by user
def validate_email(email):
	return email.endswith('@clarkson.edu')
# Before running view: assign g.user and g.session
@app.before_request
def do_get_user_session():
	g.user, g.session = get_user_session(request)

# Before running view: assign g.conf for configuration
@app.before_request
def do_set_global_conf():
	g.conf = conf
	g.navigation =[['Cosi', 'http://cslabs.clarkson.edu/'],
				['Wiki', 'http://docs.cslabs.clarkson.edu/wiki/Main_Page'],
				['Print', 'http://localhost:8080/print/login/?'],
				['Reset Password', url_for('reset_pw')],
				['Contact', url_for('contact')]]

# Root view
@app.route('/')
def index():
	return redirect(url_for('entry_point'))
		
# View for /print/ (a frame set)
@app.route('/print/')
def entry_point():
	return render_template('login.html')


# Null operation view
@app.route('/print/null/')
def null():
	return render_template('null.html')
	
# View that redirects to login or logout operations
@app.route('/print/loginout/', methods=['GET', 'POST'])
def loginout():
	if g.user.id == User.NOBODY.id:
		return redirect(url_for('login'))
	else:
		return redirect(url_for('logout'))

# Login view operation
@app.route('/print/login/', methods=['GET', 'POST'])
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
				if newuser.status == User.ST_DISABLED:
					flash('Your account has been disabled. Please contact an administrator.', 'error')
				else:
					if newuser.status == User.ST_UNVERIFIED:
						flash('Your account is unverified; you will not be allowed to print. Please check your email for a verification email.', 'warning')
					g.user = newuser
					g.session.uid = g.user.id
					g.session.Update()
					flash('Logged in as %s'%(newuser.username), 'success')
					return redirect(url_for('print_file'))
			else:
				flash('Invalid password', 'error')
	return render_template('login.html')

# Logout view operation
@app.route('/print/logout/', methods=['GET', 'POST'])
def logout():
	if request.method == 'POST':
		g.user = User.NOBODY
		g.session.uid = User.NOBODY.id
		g.session.Update()
		flash('Logged out', 'success')
	return render_template('logout.html')
	
# Registration view operation
@app.route('/print/register/', methods=['GET', 'POST'])
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
				if validate_email(email):
					newuser = User.Create(username, hashlib.sha512(password).hexdigest(), email, 0, vcode=base64.b64encode(os.urandom(conf.VER_CODE_LEN)), status=User.ST_UNVERIFIED)
					try:
						smtp=smtplib.SMTP('mail.clarkson.edu') #Moved up to avoid user ending session before email can be sent...
						smtp.sendmail('printer@cslabs.clarkson.edu', [newuser.email],render_template('verifemail.txt', vcode=newuser.vcode, username=newuser.username, email=newuser.email)) 
					except Exception:
						flash('An error occurred while sending an email. This is probably a bug; tell someone!', 'error')
					else:
						flash('Created account %s. A verification email has been sent. Check your email.'%(newuser.username), 'success')
				else: 
					flash('Invalid Clarkson Email Address. Please retype you Clarkson email correctly', 'error')
			else:
				flash('User already exists', 'error')
	return render_template('register.html')
			
# Password reset view operation
@app.route('/print/resetpw/', methods=['GET', 'POST'])
def reset_pw():
	if request.method == 'POST':
		try:
			email = request.form['email']
		except KeyError:
			flash('Bad request', 'error')
		else:
			try:
				user = User.FromEmail(email)
			except NoSuchEntity:
				flash('User with that email does not exist.', 'error')
			else:
				if user.status == User.ST_PWRESET:
					flash('A password reset is already in progress for this account.', 'error')
				elif user.status != User.ST_NORMAL:
					flash('This account is not activated yet. Contact an administrator if you need to reset it.', 'error')
				else:
					user.status = User.ST_PWRESET
					user.vcode = base64.b64encode(os.urandom(conf.VER_CODE_LEN))
					user.Update()
					try:
						smtp = smtplib.SMTP('mail.clarkson.edu')
						smtp.sendmail('printer@cslabs.clarkson.edu', [user.email], render_template('pwresetemail.txt', email = user.email, vcode = user.vcode, username = user.username))
					except Exception:
						flash('An error occured while sending an email; this is a bug! Tell someone!', 'error')
					else:
						flash('An email has been sent with further instructions; please check your mail now.', 'success')
	return render_template('resetpw.html')

# Password reset verification view operation
@app.route('/print/resetverify/')
def reset_verify():
	username = request.args['username']
	vcode = request.args['vcode']
	try:
		user = User.FromName(username)
	except NoSuchEntity:
		return 'User does not exist'
	if user.vcode != vcode:
		return 'Verification codes do not match'
	g.user = user
	g.user.status = User.ST_NORMAL
	g.user.Update()
	g.session.uid = g.user.id
	g.session.Update()
	flash('You are now logged in as yourself; when you are able, you may want to <a href="%s">set your password</a>.'%(url_for('passwd')), 'success')
	return render_template('resetverify.html')

# Password change view operation
@app.route('/print/passwd/', methods=['GET', 'POST'])
def passwd():
	if g.user.id in (User.NOBODY.id, User.ROOT.id):
		flash('You cannot set the password of this account.', 'error')
	else:
		if request.method == 'POST':
			try:
				password = request.form['password']
			except KeyError:
				flash('Bad request', 'error')
			else:
				g.user.password = hashlib.sha512(password).hexdigest()
				g.user.Update()
				flash('Password set', 'success')
	return render_template('passwd.html')

# Test page print view operation
@app.route('/print/print_test/')
def print_test():
	if g.user.status != User.ST_NORMAL:
		return 'You can\'t do that! Go away!'
	else:
		os.system('lp -U %s /home/vaillap/test.txt'%g.user.username) 
		return 'You just printed a test page!  How do you feel about yourself?'

# Print entry point view operation
@app.route('/print/', methods=['GET', 'POST'])
def print_file():
	if g.user.status == User.ST_PWRESET:
		flash('A password reset was attempted on this account. It will be cleared.', 'warning')
		g.user.status = User.ST_NORMAL
		g.user.Update()
	if g.user.status != User.ST_NORMAL:
		flash('Account disabled or not verified', 'error')
	elif request.method == 'POST':
		rfile = request.files['file']
		if rfile.filename.rpartition('.')[2] not in conf.ALLOWED_EXTENSIONS:
			flash('Bad file extension (consider printing to PDF)', 'error')
		else:
			fname = os.tmpnam()+'.'+rfile.filename.rpartition('.')[2]
			request.files['file'].save(fname)
			os.system('lp -U "%s" %s'%(g.user.username, fname))
			os.unlink(fname)
			flash('Sent to Printer', 'success')
	return render_template('print.html')
	
# Registration verification view operation
@app.route('/print/verify/')
def verify():
	username = request.args['username']
	vcode = request.args['vcode']
	try:
		user = User.FromName(username)
	except DBError:
		return 'User does not exist'
	else:
		if vcode == user.vcode:
			user.status = User.ST_NORMAL
			user.balance = conf.DEFAULT_BALANCE
			user.Update()
			return 'Success! Your account was activated.'
		else:
			return 'Bad verification code'
	return 'What the hell just happened?' 

# Contact view operatoin
@app.route('/print/contact', methods=['GET', 'POST'])
def contact():
	if request.method == 'POST':
		try:
			body = request.form['body']
		except KeyError:
			flash('Bad request', 'error')
		else:
			smtp = smtplib.SMTP('mail.clarkson.edu')
			smtp.sendmail('printer@cslabs.clarkson.edu', conf.MAINTAINERS, render_template('contactemail.txt', body = body, username = g.user.username))
			flash('Message sent successfully!', 'success')
	return render_template('contact.html')

# Test2 view operation
@app.route('/print/test2/')
def test2():
	return 'Hello from test2!'
