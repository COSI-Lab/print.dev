import sqlite3

db = sqlite3.connect('/etc/pykota/pykota.db')
cur = db.cursor()

class DBError(Exception):
	pass

class NoSuchEntity(DBError):
	pass
	
class TooManyEntities(DBError):
	pass

def _instantiate(cls, rows, attrib, val):
	if not rows:
		raise NoSuchEntity(cls, attrib, val)
	if len(rows)>1:
		raise TooManyEntities(cls, attrib, val)
	return cls(*rows[0])

class AccessEntry(object):
	def __init__(self, type, id, access, revoke=0, level=0):
		self.type   = type
		self.id     = id
		self.access = access
		self.revoke = revoke
		self.level  = level
	@classmethod
	def FromGroup(cls, group):
		if isinstance(group, Group):
			group = group.id
		cur.execute('SELECT type, id, access, revoke, level FROM acls WHERE type="group" AND id=?', (group,))
		return [cls(*row) for row in cur]
	@classmethod
	def FromUser(cls, user):
		if isinstance(user, User):
			user = user.id
		cur.execute('SELECT type, id, access, revoke, level FROM acls WHERE type="user" AND id=?', (user,))
		return [cls(*row) for row in cur]
	@classmethod
	def CreateUser(cls, user, access, revoke=0, level=0):
		if isinstance(user, User):
			user = user.id
		cur.execute('INSERT INTO acls (type, id, access, revoke, level) VALUES ("user", ?, ?, ?, ?)', (user, access, revoke, level))
		db.commit()
		return cls('user', user, access, revoke, level)
	@classmethod
	def CreateGroup(cls, group, access, revoke=0, level=0):
		if isinstance(group, Group):
			group = group.id
		cur.execute('INSERT INTO acls (type, id, access, revoke, level) VALUES ("group", ?, ?, ?, ?)', (group, access, revoke, level))
		db.commit()
		return cls('group', group, access, revoke, level)
	def Delete(self):
		cur.execute('DELETE FROM acls WHERE type=? AND id=? AND access=? AND revoke=? AND level=?', (self.type, self.id, self.access, self.revoke, self.level))
		db.commit()

class AccessToken(object):
	def __init__(self):
		self.map   = {}
		self.dirty = False
	def AddEntry(self, entry):
		self.map.setdefault(entry.access, []).append(entry)
		self.dirty = True
	def Merge(self, token):
		for k, v in token.map.iteritems():
			for entry in v:
				self.AddEntry(entry)
	@classmethod
	def FromGroup(cls, group):
		self = cls()
		for entry in AccessEntry.FromGroup(group):
			self.AddEntry(entry)
		if group.inherit: # XXX is not None
			self.Merge(cls.FromGroup(group.inherit))
		return self
	@classmethod
	def FromUser(cls, user):
		self = cls()
		if not isinstance(user, User):
			user = User.FromID(user)
		for entry in AccessEntry.FromUser(user):
			self.AddEntry(entry)
		for group in user.Groups():
			self.Merge(cls.FromGroup(group))
		return self
	def Optimize(self):
		for k, v in self.map.iteritems():
			v.sort(key=lambda entry: entry.level*2+(1 if entry.revoke else 0))
		self.dirty = False
	def GetAccessEntry(self, access):
		if self.dirty:
			self.Optimize()
		return self.map.get(access, [None])[-1]
	def GetAccess(self, access):
		ent = self.GetAccessEntry(access)
		if ent is None:
			return False
		return not ent.revoke

class Group(object):
	def __init__(self, id, name, inherit):
		self.id      = id
		self.name    = name
		self.inherit = inherit
		if isinstance(self.inherit, (long, int)):
			try:
				self.inherit = Group.FromID(self.inherit)
			except DBError:
				pass
	@classmethod
	def FromID(cls, id):
		cur.execute('SELECT id, name, inherit FROM acgroups WHERE id=?', (id,))
		return _instantiate(cls, cur.fetchall(), 'id', id)
	@classmethod
	def FromName(cls, name):
		cur.execute('SELECT id, name, inherit FROM acgroups WHERE name=?', (name,))
		return _instantiate(cls, cur.fetchall(), 'name', name)
	@classmethod
	def Create(cls, name, inherit):
		if isinstance(inherit, Group):
			inherit = inherit.id
		cur.execute('INSERT INTO acgroups (name, inherit) VALUES (?, ?)', (name, inherit))
		db.commit()
		return cls(cur.lastrowid, name, inherit)
	def Update(self):
		cur.execute('UPDATE acgroups SET name=?, inherit=? WHERE id=?', (self.name, self.inherit.id if isinstance(self.inherit, Group) else self.inherit, self.id))
		db.commit()
	def Delete(self):
		cur.execute('DELETE FROM acmembership WHERE gid=?', (self.id,))
		cur.execute('DELETE FROM acgroups WHERE id=?', (self.id,))
		db.commit()
	def Users(self):
		cur.execute('SELECT uid FROM acmembership WHERE gid=?', (self.id,))
		res = []
		for row in cur:
			try:
				res.append(User.FromID(row[0]))
			except DBError:
				res.append(row[0])
		return res
	def AddUser(self, user):
		if isinstance(user, User):
			user = user.id
		cur.execute('INSERT INTO acmembership (gid, uid) VALUES (?, ?)', (self.id, user))
		db.commit()
	def RemoveUser(self, user):
		if isinstance(user, User):
			user = user.id
		cur.execute('DELETE FROM acmembership WHERE gid=? AND uid=?', (self.id, user))
		db.commit()
	def AccessToken(self):
		return AccessToken.FromGroup(self)

class User(object):
	def __init__(self, id, username, password, email, balance, overcharge):
		self.id         = id
		self.username   = username
		self.password   = password
		self.email      = email
		self.balance    = balance
		self.overcharge = overcharge
	@classmethod
	def FromID(cls, id):
		cur.execute('SELECT id, username, password, email, balance, overcharge FROM users WHERE id = ?', (id,))
		return _instantiate(cls, cur.fetchall(), 'id', id)
	@classmethod
	def FromName(cls, name):
		cur.execute('SELECT id, username, password, email, balance, overcharge FROM users WHERE username = ?', (name,))
		return _instantiate(cls, cur.fetchall(), 'name', name)
	@classmethod
	def Create(cls, username, password, email, balance, overcharge=1):
		cur.execute('INSERT INTO users (username, password, email, limitby, balance, overcharge) VALUES(?, ?, ?, "balance", ?, ?)', (username, password, email, balance, overcharge))
		db.commit()
		return cls(cur.lastrowid, username, password, email, balance, overcharge)
	def Update(self):
		cur.execute('UPDATE users SET username=?, password=?, email=?, balance=?, overcharge=? WHERE id=?', (self.username, self.password, self.email, self.balance, self.overcharge, self.id))
		db.commit()
	def Delete(self):
		cur.execute('DELETE FROM acmembership WHERE uid=?', (self.id,))
		cur.execute('DELETE FROM users WHERE id=?', (self.id,))
		db.commit()
	def Groups(self):
		cur.execute('SELECT gid FROM acmembership WHERE uid=?', (self.id,))
		res = []
		for row in cur:
			try:
				res.append(Group.FromID(row[0]))
			except DBError:
				res.append(row[0])
		return res
	def AddToGroup(self, group):
		if isinstance(group, Group):
			group = group.id
		cur.execute('INSERT INTO acmembership (gid, uid) VALUES (?, ?)', (group, self.id))
		db.commit()
	def RemoveFromGroup(self, group):
		if isinstance(group, Group):
			group = group.id
		cur.execute('REMOVE FROM acmembership WHERE gid=? AND uid=?', (group, self.id))
		db.commit()
	def AccessToken(self):
		return AccessToken.FromUser(self)

# Constants--do not touch

User.ROOT   = User.FromID(1)
User.NOBODY = User.FromID(2)
