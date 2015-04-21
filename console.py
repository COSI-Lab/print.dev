import cmd
import shlex
import getpass
import traceback
import fnmatch
import hashlib

import userdb

def match_users(pat):
	# XXX reimplement?
	import fnmatch
	if ':' in pat:
		tp, col, pat = pat.partition(':')
	else:
		tp = 'U'
	if tp == 'U':
		return filter(lambda u, pat=pat, fnmatch=fnmatch: fnmatch.fnmatch(str(u.username), pat), userdb.User.All())
	elif tp == 'E':
		return filter(lambda u, pat=pat, fnmatch=fnmatch: fnmatch.fnmatch(str(u.email), pat), userdb.User.All())
	elif tp == 'S':
		return filter(lambda u, pat=pat, fnmatch=fnmatch: fnmatch.fnmatch(str(STATUS_NAMES.get(u.status)), pat), userdb.User.All())
	raise ValueError('Unknown class: %s'%(tp))

class TP:
	STRING=0
	INT=1
	FLOAT=2
	USERS=3
	USER=4
	EXPR=5
	DEF_NAMES = {STRING: 'a string', INT: 'an integer', FLOAT: 'a floating point', USERS: 'a user pattern', USER: 'a single-user pattern', EXPR: 'a Python expression'}

_STATUS_NAMES = ['NORMAL', 'DISABLED', 'UNVERIFIED', 'PWRESET']
STATUS_NAMES = {}
for idx, v in enumerate(_STATUS_NAMES):
	STATUS_NAMES[idx]=v

class PrintConsole(cmd.Cmd):
	prompt = '?> '
	intro = 'Print Server User Console\n(Try `help` and `help <command>`)'
	def onecmd(self, s):
		try:
			cmd.Cmd.onecmd(self, s)
		except Exception, e:
			print '!!! An error occurred during the command:', s
			import traceback
			traceback.print_exc()
	def _expect(self, line, *types):
		parts = shlex.split(line)
		ret = []
		for tp in types:
			if not parts:
				raise TypeError('Expected '+(tp[1] if len(tp)>1 else TP.DEF_NAMES[tp[0]]))
			part = parts[0]
			parts = parts[1:]
			if tp[0] == TP.STRING:
				ret.append(part)
			elif tp[0] == TP.INT:
				ret.append(int(part))
			elif tp[0] == TP.FLOAT:
				ret.append(float(part))
			elif tp[0] in (TP.USERS, TP.USER):
				ret.append(match_users(part))
				if tp[0] == TP.USER:
					if len(ret[0]) != 1:
						raise ValueError('User pattern produced %d matches instead of 1'%(len(ret[0])))
				if len(ret[0]) == 0:
					print 'Warning: user pattern matched zero users'
			elif tp[0] == TP.EXPR:
				ret.append(eval(part))
		return ret
	def do_quit(self, line):
		'''quit

Quits the program.'''
		print('Goodbye.')
		exit()
	def do_view(self, line):
		'''view <users>

View information about the users matching the given pattern.'''
		users = self._expect(line, (TP.USERS,))[0]
		self.show_pat(users)
	def show_pat(self, users):
		print 'Matched', len(users), 'rows:'
		hdr = '{name:20}{email:32}{status:14}{balance:8}{overcharge:8}'.format(name='USERNAME', email='EMAIL', status='STATUS', balance='BAL', overcharge='OVRCHRG')
		print hdr
		print '='*len(hdr)
		for u in users:
			status = STATUS_NAMES.get(u.status, repr(u.status)+'?!')
			print '{u.username:20}{u.email:32}{status:14}{u.balance:8}{u.overcharge:8}'.format(u=u, status=status)
	def confirm(self, prompt):
		ch = ''
		while not ch:
			ch = raw_input(prompt+'[y/n] ')
		if ch.lower()[0] != 'y':
			raise RuntimeError('Aborted.')
	def do_status(self, line):
		'''status <names> <status>

Set the status of an account.

Currently legal statuses include 0 (NORMAL), 1 (DISABLED), 2 (UNVERIFIED), 3 (PWRESET). See userdb for more information.

See also enable, disable, verify, passwd.'''
		users, status = self._expect(line, (TP.USERS,), (TP.INT,))
		sname = STATUS_NAMES.get(status) 
		if sname is None:
			raise ValueError('Unknown status specified: %d'%(status))
		self.show_pat(users)
		self.confirm('Set status to %s? '%(sname))
		for u in users:
			u.status = status
			u.Update()
	def do_passwd(self, line):
		'''passwd <user>

Change the password of a user.'''
		user = self._expect(line, (TP.USER,))
		self.show_pat([user])
		self.confirm('Change password of %s? '%(user.username))
		u.password = hashlib.sha512(getpass.getpass('Password: ')).hexdigest()
		u.Update()
	def do_balance(self, line):
		'''balance <users> [+|-]<amt>

Set, add, or subtract balance to or from the specified users. Specifying + or - will add or subtract, respectively; without either, the balance is set.'''
		users, amt = self._expect(line, (TP.USERS,), (TP.STRING,))
		if amt[0]=='-':
			mode = 2
			amt = amt[1:]
		elif amt[0]=='+':
			mode = 1
			amt = amt[1:]
		else:
			mode = 0
		amt = float(amt)
		self.show_pat(users)
		if mode == 0:
			self.confirm('Set balance to %f? '%(amt))
		elif mode == 1:
			self.confirm('Add %f to balance? '%(amt))
		elif mode == 2:
			self.confirm('Subtract %f from balance? '%(amt))
		for u in users:
			if mode == 0:
				u.balance = amt
			elif mode == 1:
				u.balance += amt
			elif mode == 2:
				u.balance -= amt
			u.Update()
	def do_enable(self, line):
		'''enable <users>

Alias to `status <users> 0`'''
		arg = self._expect(line, (TP.STRING,))[0]
		self.onecmd('status "'+arg+'" 0')
	def do_disable(self, line):
		'''disable <users>

Alias to `status <users> 1`'''
		arg = self._expect(line, (TP.STRING,))[0]
		self.onecmd('status "'+arg+'" 1')
	def do_verify(self, line):
		'''verify <users>

Alias to `status <users> 0`'''
		arg = self._expect(line, (TP.STRING,))[0]
		self.onecmd('status "'+arg+'" 0')
	def do_q(self, line):
		'''q

Alias to `quit`'''
		self.onecmd('quit')
	def help_userpat(self, *whatever):
		print '''User Patterns:

User patterns are used wherever users may be specified. The present implementation is documented as follows:
The pattern is to be prefixed with a scheme, followed by a colon, as follows:
<scheme>:<pattern>
If the colon is omitted entirely, the scheme defaults to 'U'.
The schemes are as follows:
-U: Match against usernames using fnmatch (shell globbing)
-E: Match against emails using fnmatch (shell globbing)
-S: Match against status names using fnmatch (shell globbing)

This implementation is subject to change.'''


if __name__ == '__main__':
	interp = PrintConsole()
	interp.cmdloop()
