'''
print -- CSLabs Print Server
sessiondb -- Session Database

This is an sqlite module in the same vein as userdb (see), and supports many of
the same interfaces; however, it is intentionally separated as:
-It does not share a database, and
-the database it uses has different privileges for access.
It is thus suitable for processes that don't require elevation to whatever account
would be required to access the pykota database that userdb uses for modification.

This module exports one object, the Session, which is mutable by the definitions
established in userdb. It is backed by the "sessions" table, and has the following
useful attributes:
-session.id is the unique ID of the session, and
-session.uid is the user ID associated with this session.

Sessions may be created using Session.FromID, the same as the Group and User classes,
and will incur the same error. Sessions do not have names, and so do not possess a
FromName classmethod.

A Session may also be created by passing .Create() a User or user ID. This will create
and return a new Session object with a unique ID.

Sessions support .Update() and .Delete() as with Users and Groups.

Finally, as a convenience, calling session.User() will return the User associated with
the Session, or raise a NoSuchEntity error.
'''

import sqlite3
import os

from userdb import _instantiate, User

db = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'sessions.db'), check_same_thread = False)
cur = db.cursor()

class Session(object):
	def __init__(self, id, uid):
		self.id  = id
		self.uid = uid
	@classmethod
	def FromID(cls, id):
		cur.execute('SELECT id, uid FROM sessions WHERE id=?', (id,))
		return _instantiate(cls, cur.fetchall(), 'id', id)
	@classmethod
	def Create(cls, user):
		if isinstance(user, User):
			user = user.id
		cur.execute('INSERT INTO sessions (uid) VALUES (?)', (user,))
		db.commit()
		return cls(cur.lastrowid, user)
	def Update(self):
		cur.execute('UPDATE sessions SET uid=? WHERE id=?', (self.uid, self.id))
		db.commit()
	def Delete(self):
		cur.execute('DELETE FROM sessions WHERE id=?', (self.id,))
		db.commit()
	def User(self):
		return User.FromID(self.uid)
