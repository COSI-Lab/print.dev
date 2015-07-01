import cmd
import shlex
import getpass
import traceback
import fnmatch
import hashlib
import time
import sys

import userdb

def match_users(pat):
	res = set()
	for part in pat.split(','):
		res |= match_terms(part)
	return res

def match_terms(pat):
	# XXX reimplement?
	users = userdb.User.All()
	uset = set(users)
	ret = set(users)
	for part in pat.split(';'):
		if part[0] == '!':
			pset = uset - set(match_pat(part[1:], users))
		else:
			pset = set(match_pat(part, users))
		ret &= pset
	return ret

def match_pat(pat, users):
	if ':' in pat:
		tp, col, pat = pat.partition(':')
	else:
		tp = 'U'
	if tp == 'U':
		return filter(lambda u, pat=pat, fnmatch=fnmatch: fnmatch.fnmatch(str(u.username), pat), users)
	elif tp == 'u':
		return filter(lambda u, pat=int(pat): u.id == pat, users)
	elif tp == 'E':
		return filter(lambda u, pat=pat, fnmatch=fnmatch: fnmatch.fnmatch(str(u.email), pat), users)
	elif tp == 'S':
		return filter(lambda u, pat=pat, fnmatch=fnmatch: fnmatch.fnmatch(str(STATUS_NAMES.get(u.status)), pat), users)
	elif tp == 'B':
		if pat[0] == '<':
			return filter(lambda u, pat=float(pat[1:]): u.balance<pat, users)
		elif pat[0] == '>':
			return filter(lambda u, pat=float(pat[1:]): u.balance>pat, users)
		elif pat[0] == '=':
			return filter(lambda u, pat=float(pat[1:]): u.balance==pat, users)
		elif pat[0:2] == '<=':
			return filter(lambda u, pat=float(pat[2:]): u.balance<=pat, users)
		elif pat[0:2] == '>=':
			return filter(lambda u, pat=float(pat[2:]): u.balance>=pat, users)
		elif pat[0:2] == '==':
			return filter(lambda u, pat=float(pat[2:]): u.balance==pat, users)
		return filter(lambda u, pat=float(pat): u.balance==pat, users)
	elif tp == 'O':
		if pat[0] == '<':
			return filter(lambda u, pat=float(pat[1:]): u.overcharge<pat, users)
		elif pat[0] == '>':
			return filter(lambda u, pat=float(pat[1:]): u.overcharge>pat, users)
		elif pat[0] == '=':
			return filter(lambda u, pat=float(pat[1:]): u.overcharge==pat, users)
		elif pat[0:2] == '<=':
			return filter(lambda u, pat=float(pat[2:]): u.overcharge<=pat, users)
		elif pat[0:2] == '>=':
			return filter(lambda u, pat=float(pat[2:]): u.overcharge>=pat, users)
		elif pat[0:2] == '==':
			return filter(lambda u, pat=float(pat[2:]): u.overcharge==pat, users)
		return filter(lambda u, pat=float(pat): u.overcharge==pat, users)
	raise ValueError('Unknown class: %s'%(tp))

NAG_SECONDS = 10
NAG_RESOLUTION = 4

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
		hdr = '{id:8}{name:20}{email:32}{status:14}{balance:8}{overcharge:8}'.format(id='ID', name='USERNAME', email='EMAIL', status='STATUS', balance='BAL', overcharge='OVRCHRG')
		print hdr
		print '='*len(hdr)
		for u in users:
			status = STATUS_NAMES.get(u.status, repr(u.status)+'?!')
			print '{u.id:<8}{u.username:20}{u.email:32}{status:14}{u.balance:<8}{u.overcharge:<8}'.format(u=u, status=status)
	def confirm(self, prompt):
		ch = ''
		while not ch:
			ch = raw_input(prompt+'[y/n] ')
		if ch.lower()[0] != 'y':
			raise RuntimeError('Aborted.')
	def do_status(self, line):
		'''status <names> <status>

Set the status of an account.

Currently legal statuses are listed in `help statuses`. See userdb for more information.

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
		user = self._expect(line, (TP.USER,))[0][0]
		self.show_pat([user])
		self.confirm('Change password of %s? '%(user.username))
		passwd = getpass.getpass('Password: ')
		if passwd:
			passwd = hashlib.sha512(passwd).hexdigest()
		user.password = passwd
		user.Update()
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
	def do_overcharge(self, line):
		'''overcharge <users> <ovrchrg>

Set the overcharge of the specified users. Overcharge represents a constant multiple when computing cost; the balance of a user after a job is computed more-or-less as:

balance -= overcharge * num_pages

with the special restriction that, if the new balance as computed by foreknowledge of the number of pages is negative, the job is cancelled.

Overcharge can be negative, in which case users gain balance by printing.'''
		users, ovrc = self._expect(line, (TP.USERS,), (TP.FLOAT,))
		self.show_pat(users)
		self.confirm('Set overcharge to %f? '%(ovrc))
		for u in users:
			u.overcharge = ovrc
			u.Update()
	def do_create(self, line):
		'''create <username> <email>

Create a new user account. The account will be immediately active, limited by balance, capable of printing normally, but with zero balance (that would prevent it). Use `balance <username>` to set balance afterward.

You will be prompted for a password for the user. Entering an empty string will lock the account--see `help passwd`.'''
		username, email = self._expect(line, (TP.STRING,), (TP.STRING,))
		self.confirm('Create user %s with email %s? '%(username, email))
		passwd = getpass.getpass('Password: ')
		if passwd:
			passwd = hashlib.sha512(passwd).hexdigest()
		userdb.User.Create(username, passwd, email, 0, 1.0, None, userdb.User.ST_NORMAL)
	def do_remove(self, line):
		'''remove <users>

Remove the specified users. This action CANNOT be undone.'''
		users = self._expect(line, (TP.USERS,))[0]
		self.show_pat(users)
		print 'NOTE: You will be asked TWICE whether or not you would like to complete this action.'
		print 'Deleting users is generally HIGHLY DISCOURAGED, and you SHOULD NOT DO THIS unless you have to.'
		print 'For a better alternative, see `help status` (or `help disable`).'
		if not hasattr(self, 'nagged'):
			print '---PLEASE read the above---'
			for i in range(NAG_SECONDS * NAG_RESOLUTION):
				print (NAG_SECONDS - float(i)/NAG_RESOLUTION),
				sys.stdout.flush()
				time.sleep(1.0/NAG_RESOLUTION)
			print
			self.nagged = True
			print 'Nag complete, you will not have to wait the next time in this session.'
		self.confirm('Delete these users?')
		self.confirm('REALLY delete these users?')
		for u in users:
			u.Delete()
		userdb.db.commit()
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
A pattern is a disjunction of term patterns; each component is separated by a comma (","). With more than one term pattern, the union of the criteria is generated.
A term pattern may be specified by a pattern component; these are separated by semicolons (";"). When more than one component is given, the intersection of the criteria is generated.
A term component may be negated by prefixing a "!".
The pattern component prefixed with a scheme, followed by a colon, as follows:
<scheme>:<pattern>
If the colon is omitted entirely, the scheme defaults to 'U'.
The schemes are as follows:
-U: Match against usernames using fnmatch (shell globbing)
-u: Match against a numeric user id exactly
-E: Match against emails using fnmatch (shell globbing)
-S: Match against status names using fnmatch (shell globbing)
-B: Match against balance. You may prefix a balance with any of <, >, <=, >=, =, ==; if none is provided, = is assumed.
-O: Match against overcharge. Comparisons are as for balance, above.

Example patterns:
Users starting with "doe": "U:doe*" or just "doe*"
Users whose emails don't end with ".edu": "!E:*.edu"
Users whose balance is below 10.0 and who are not unverified: "B:<10;!S:UNV*"
Users who are unverified or in password reset: "S:UNV*,S:PWR*"
Users with no status: "S:*!"
User id 5: "u:5"

This implementation is subject to change.'''
	def help_statuses(self, *whatever):
		print '''User Statuses:

User statuses are singular, orthogonal assignments to users handled by the user system. For more information on
each one and its implications, please see userdb.

The statuses known to the system are as follows (note that `status` expects a number, but the `S:` userpat
uses a name; see `help userpat`:'''
		for val, name in STATUS_NAMES.iteritems():
			print '%d\t%s'%(val, name)


if __name__ == '__main__':
	interp = PrintConsole()
	interp.cmdloop()
