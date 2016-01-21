'''
print -- CSLabs Print Server
conf -- Configuration

This module contains some variables that can be modified to configure the web application.
In general, these variables are used to provide defaults for actions that are done
via the web interface. They should not be used in any other scenario, particularly in
places where the web interface is irrelevant.

The following are defined:
-DEFAULT_BALANCE is the balance given to newly created accounts.
-ALLOWED_EXTENSIONS are the file extensions the print API will consider printing (these
 are exploitable, as the client controls the filename, but PyKota will still use valid
 page calculations for balance estimates.
-VER_CODE_LEN is the size of a verification code (in bytes, not in characters; it's
 usually b64 encoded).
-MAINTAINERS is a list of emails that will receive messages sent through the contact form.
'''

class ExtenAllowAll(object):
	def __iter__(self):
		return iter(['frickin\' everything'])
	def __contains__(self, obj):
		return True

DEFAULT_BALANCE = 200
ALLOWED_EXTENSIONS = sorted(["txt", "pdf", "ps", "png", "jpg", "jpeg", "gif", "tex", "prn", "c", "cpp", "h", "hpp", "java", "pl", "py", "php", "sh", "b", "xml", "conf", "asm", "bat", "bib", "cs", "erl", "ini", "js", "lisp", "sql", "m", "pas", "patch", "pro", "scm", "hs", "sol"])
CONVERTABLE_EXTENSIONS = sorted(["docx", "doc","odt","pptx","ppt","odp","xlsx","xls","ods","csv","odf","odg","rtf"])
ALL_EXTENSIONS = sorted(ALLOWED_EXTENSIONS+CONVERTABLE_EXTENSIONS)
#ALLOWED_EXTENSIONS = ExtenAllowAll()
VER_CODE_LEN = 16
MAINTAINERS = [
	'northug@clarkson.edu',
	'lannonbr@clarkson.edu',
]
MX = 'aspmx.l.google.com'
