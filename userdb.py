'''
print -- CSLabs Print Server
userdb -- User Database

This module handles most of the low-level interfacing with the pykota sqlite3 database.
In particular, it provides four classes that abstract away the database schema:

-The User class, which describes a single user (as pykota recognizes it) and is backed
 by the table "users".
-The Group class, which describes an entity which contains zero or more users, and is
 backed by the (non-pykota) table "acgroups".
-The AccessEntry class, which describes an entry in the (non-pykota) "acls" table, which
 describes an access right that is granted or revoked from a user or group.
-The AccessToken class, which is *not* backed by a table, but instead coalesces and
 interprets the AccessEntries for a particular Group or User.
 
Additionally, the intersection table "acmemberships" exists, which is not described by
any class in this module, but which is manipulated by both Users and Groups.

The User and Group classes are both *mutable*; they contain within them an identifier
(attribute .id) that contains their unique entry in the table that backs them (in sqlite
parlance, this is the "rowid"). However, changes to their values are not saved immediately
(to protect consistency of the database); rather, after all values are updated, the
application must call .Update() on these instances to update their values into the database.
These transactions are carried out atomically, which may not preserve consistency between
entities in relations; there is no public API for preserving this yet.

Here's a small example which adds 20.0 credits to a users balance, assuming the local
variable "user" is a User object:

	user.balance+=20
	user.Update()

Acquiring a User object is fairly easy; when dealing with the database, you will typically
find user ids scattered everywhere. Given an ID (an integer), getting the User object is
almost trivial:

	user = User.FromID(user_id)
	
It should be noted that this call can raise NoSuchEntity (a DBError, defined herein) if
that id does not correspond to a user.

Elsewhere (especially outside the database), you may see users referred to by name. Again,
getting such a reference is quite easy:

	user = User.FromName(user_name)
	
In addition to raising NoSuchEntity (if a user by that name does not exist), this can also
raise TooManyEntitites (another DBError), indicating that multiple users go by that name.
This is a condition which may occur due to lack of enforcement of username uniqueness in
the schema; if you're looking for a truly unique identifier, use the UID. If you wish to
verify that a user does or does not exist, try to find it (using User.FromName) first.

After getting a user object, there are some attributes that are generally useful, corresponding
to columns in the users table:

-user.id is the user ID (don't write to this),
-user.username is the user's name,
-user.password is the hexadecimal SHA-512 hash of that user's password (as returned by
 hashlib.sha512('<password>').hexdigest()),
-user.email is the email the user signed up with,
-user.balance is the user's balance, and
-user.overcharge is the user's overcharge factor (how much of their credit they are paying
 per print job; see pykota's documentation for more details. This value may be negative!)
 
Two special user objects exist: they are User.ROOT and User.NOBODY. Their IDs are User.ID_ROOT
and User.ID_NOBODY respectively; they represent the root user with all access privileges and
the default account assumed by users that haven't presented credentials to log in to a particular
account, respectively. User.ROOT's access token is specialized; see below.

Groups are very similar objects in that they have an ID and a name, and can thusly be gotten:

	group = Group.FromID(group_id)
	group = Group.FromName(group_name)
	
Both calls may raise exactly the same errors as would be raised by the analogous classmethods
on users.

Groups have the following attributes:

-group.id is the group ID (don't write to this),
-group.name is the group name,
-group.inherit is a Group or group ID of a group from which this group inherits (that is to
 say, this attribute represents the parent group), or None of this group does not inherit
 from any group.
 
Inheritance is discussed with AccessTokens, below.

A group may be queried for its users:

	users = group.Users()
	
In this case, users will be a list of:
-User objects, if the users could be found in the database, and
-user IDs, as integers, if those IDs don't correspond to users in the database.
The former case is most likely.

Similarly, a user can be queried for its groups:

	groups = user.Groups()
	
This will be a similar list of Group objects and unresolvable group IDs, if the latter exist.

Group membership can be adjusted by using any of four methods:

	group.AddUser(user)
	group.RemoveUser(user)
	user.AddToGroup(group)
	user.RemoveFromGroup(group)
	
These calls do *not* require calls to .Update(); they will update the database automatically
(but they will *not* update attributes on the object that is used in the call; this is what
.Update() does explicitly). All four calls may also accept a group or user ID in place of
a Group or User, respectively.

Finally, both users and groups can be deleted by using the .Delete() method:

	user.Delete()
	group.Delete()
	
This action cannot be undone; use it with care.

An AccessEntry is much like the above classes in certain respects; however, it is immutable,
and so it does *not* provide the .Update() method. It does, however, provide the .Delete()
method, so the proper way to ".Update()" an AccessEntry is to:
1. Make a new AccessEntry, with the values properly updated in the .CreateXxx() call, then
2. Delete the old AccessEntry.

An AccessEntry is created with two .CreateXxx() methods:
-.CreateUser() creates an AccessEntry associated with a user, and
-.CreateGroup() creates an AccessEntry associated with a group.

Regardless of which method is used, these constructors both accept:
-an access string, which is domain-specific and may be chosen at will by the developers of
 the application,
-a revocation status (either 0 or 1) which describes whether or not the access is being
 granted or revoked (by default, it is granted), and
-a level, which determines how this may override other grants and revocations.

Ultimately, determining the effective access of a user for an accessible resource is
determined by the following:
-First, a set of AccessEntries describing the object is acquired. For a User, this consists
 of AccessEntries describing the user, and all of the AccessEntries describing that user's
 groups. For a Group, this consists of the AccessEntries describing that group, and all of
 the AccessEntries describing its parent groups (the ones from which it inherits, directly
 or indirectly).
-Then, this set is sorted into a sequence, by the AccessEntry's level. The AccessEntries
 with a maximal level are kept, and the rest are discarded.
-Finally, this set is tested for revocations; a revocation will always override a grant.
 If no revocations exist, and the set is not empty, access is granted. Otherwise, it is denied.

This is exactly the algorithm which constructs an AccessToken, which is a cached result of
applying all of these policies to all of the AccessEntries describing a particular entity.
An AccessToken can be constructed for a particular user or group by calling that object's
.AccessToken() method:

	at = user.AccessToken()
	at = group.AccessToken()
	
Additionally, the AccessToken methods themselves can be called with either User or Group
objects or respective IDs; the above methods are just shortcuts for these:

	at = AccessToken.FromUser(user)
	at = AccessToken.FromGroup(group)
	
To actually check access (verify whether access is granted for a particular access string),
use .GetAccess():

	if at.GetAccess('do-something'):
		print 'Access granted to do-something!'
	else:
		print 'Access denied to do-something!'
		
One may also use .GetAccessEntry() to get the AccessEntry (determined by the policies above)
which is responsible for granting or denying access, or None if no such AccessEntry exists:

	ae = at.GetAccessEntry('do-something')
	if ae is not None:
		print 'Access '+('revoked' if ae.revoke else 'granted')+' at level '+str(ae.level)
	else:
		print 'Access denied by default (no entries)'
		
The root user (User.ROOT) has a special-cased AccessToken (actually a GrantAllAccessToken)
that grants that user all privileges in the system. However, the root user, by default, has
no password. Use this account with care; the system will not prevent it from doing anything,
even harmful things!
'''

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

class GrantAllAccessToken(AccessToken):
	def __init__(self):
		pass
	def GetAccess(self, access):
		return True

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
	ID_ROOT = 1
	ID_NOBODY = 2
	ST_NORMAL = 0
	ST_DISABLED = 1
	ST_UNVERIFIED = 2
	ST_PWRESET = 3
	def __init__(self, id, username, password, email, balance, overcharge, vcode, status):
		self.id         = id
		self.username   = username
		self.password   = password
		self.vcode	= vcode
		self.status	= status
		self.email      = email
		self.balance    = balance
		self.overcharge = overcharge
	@classmethod
	def All(cls):
		ret = []
		for row in cur.execute('SELECT id, username, password, email, balance, overcharge, vcode, status FROM users'):
			ret.append(cls(*row))
		return ret
	@classmethod
	def FromID(cls, id):
		cur.execute('SELECT id, username, password, email, balance, overcharge, vcode, status FROM users WHERE id = ?', (id,))
		return _instantiate(cls, cur.fetchall(), 'id', id)
	@classmethod
	def FromName(cls, name):
		cur.execute('SELECT id, username, password, email, balance, overcharge, vcode, status FROM users WHERE username = ?', (name,))
		return _instantiate(cls, cur.fetchall(), 'name', name)
	@classmethod
	def FromEmail(cls, email):
		cur.execute('SELECT id, username, password, email, balance, overcharge, vcode, status FROM users WHERE email = ?', (email,))
		return _instantiate(cls, cur.fetchall(), 'email', email)
	@classmethod
	def Create(cls, username, password, email, balance, overcharge=1, vcode=None, status=ST_NORMAL):
		cur.execute('INSERT INTO users (username, password, email, limitby, balance, overcharge, vcode, status) VALUES(?, ?, ?, "balance", ?, ?, ?, ?)', (username, password, email, balance, overcharge, vcode, status))
		db.commit()
		return cls(cur.lastrowid, username, password, email, balance, overcharge, vcode, status)
	def Update(self):
		cur.execute('UPDATE users SET username=?, password=?, email=?, balance=?, overcharge=? , vcode=? , status=? WHERE id=?', (self.username, self.password, self.email, self.balance, self.overcharge, self.vcode, self.status, self.id))		
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
		# XXX Special casing (also see below)
		if self.id == self.ID_ROOT:
			return GrantAllAccessToken()
		return AccessToken.FromUser(self)

# Constants--do not touch

User.ROOT   = User.FromID(User.ID_ROOT)
User.NOBODY = User.FromID(User.ID_NOBODY)
