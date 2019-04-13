import re
import traceback
import conf
import os

from flask import Flask, render_template, redirect, url_for, request, g, flash


app = Flask('print')
app.debug = True

valid_page = re.compile("^[-,0-9]*$")

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

# Before running view: assign g.conf for configuration
@app.before_request
def do_set_global_conf():
	g.conf = conf

# Print entry point view operation
@app.route('/', methods=['GET', 'POST'])
def print_file():
	if request.method == 'POST':
		options = []
		rfile = request.files['file']
		copies = request.values.get('copies', 1, int)
		options.append('-n %d'%(copies,))
		pages = request.values.get('pages', '')
		collate = request.values.get('collate', '')
		if not valid_page.match(pages):
			flash('Bad page format', 'error')
			return render_template("print.html")
		if pages:
			options.append('-P "%s"'%(pages,))
		if collate:
			options.append('-o Collate=True')
		duplex = request.values.get('duplex', False, bool)
		options.append('-o sides=two-sided-long-edge' if duplex else '-o sides=one-sided')
		options.append('-o media=Letter')
		options.append('-t \'%s\''%(rfile.filename.replace("'", '_')))
		if rfile.filename.rpartition('.')[2].lower() in conf.ALLOWED_EXTENSIONS:
            fname = os.tmpnam()+'.'+rfile.filename.rpartition('.')[2]
			request.files['file'].save(fname)
            os.system('lp %s %s'%(' '.join(options), fname))
            os.unlink(fname)
            flash('Sent to Printer', 'success')
		elif rfile.filename.rpartition('.')[2].lower() in conf.CONVERTABLE_EXTENSIONS:
            fname = os.tmpnam()+'.'+rfile.filename.rpartition('.')[2]
			request.files['file'].save(fname)
			tmp_fold = os.path.dirname(fname)
			os.system('soffice --headless --convert-to pdf --outdir %s %s'%(tmp_fold,fname))
			conv_base, tmp_ext = os.path.splitext(fname);
			fname_pdf = conv_base+'.pdf'
			os.system('lp %s %s'%(' '.join(options), fname_pdf))
            os.unlink(fname)
			os.unlink(fname_pdf)
            flash('Sent to Printer', 'success')
		else:
			flash('Bad file extension (consider printing to PDF)', 'error')
	return render_template('print.html')
