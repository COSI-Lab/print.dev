from wsgiref.simple_server import make_server
# XXX Hack
pr = __import__('print')

httpd = make_server('', 8080, pr.app)

httpd.serve_forever()
