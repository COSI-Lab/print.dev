import sqlite3

from userdb import _instantiate, User

db = sqlite3.connect('sessions.db')
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
