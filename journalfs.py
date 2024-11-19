#!/home/khuxkm/project/venv/bin/python3
import pyinotify, uuid, sqlite3, atexit, time, os
from dmphelper import diff, patch
from collections import namedtuple

watchman = pyinotify.WatchManager()
watchmask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_DELETE

db = sqlite3.connect("journal.db")

db.execute("CREATE TABLE IF NOT EXISTS journals (uuid TEXT PRIMARY KEY, path TEXT, ctime INTEGER, dtime INTEGER);")
db.execute("CREATE TABLE IF NOT EXISTS entries (journal TEXT, delta TEXT, mtime INTEGER, FOREIGN KEY (journal) REFERENCES journals (uuid));")
db.commit()

def _close_db(db):
	db.commit()
	db.close()
atexit.register(_close_db, db)

def log(msg,c="*"):
	print(f"[{c}] {msg}")

FakeEvent = namedtuple("FakeEvent",["name"])

N = 5 # maximum entries in the list

class Journaler(pyinotify.ProcessEvent):
	def __init__(self):
		super(Journaler, self).__init__()
		self.journals = {}
		self.contents = {}
		# open active journals from the last time we were running
		cur = db.cursor()
		cur.execute("SELECT path, uuid FROM journals WHERE dtime = -1")
		journals = cur.fetchall()
		for name, journal in journals:
			log(f"Reopening journal {journal} for file {name}")
			self.journals[name] = journal
			# our methodology here is to store the diffs of our file at each modify
			# the oldest diff is always from an empty string:
			# - content in the file when it was created? we calculated the diff from empty string then
			# - no content in the file when it was created? we calculated the diff from empty string on first modify
			# - rotated the circular journal? we changed the new oldest diff to be from empty string
			# so we can always start from empty string and get to anywhere in our journal
			content = ""
			cur.execute("SELECT delta FROM entries WHERE journal = ? ORDER BY mtime ASC",[journal])
			for delta in cur.fetchall():
				content = patch(content,delta[0]) # delta is a 1-item tuple
			self.contents[name] = content
			try:
				with open("watched/"+name) as f: realcontent = f.read()
				if realcontent!=content: self.process_IN_MODIFY(FakeEvent(name))
			except FileNotFoundError:
				log("...File is gone.")
				self.process_IN_DELETE(FakeEvent(name))
	def process_IN_CREATE(self,event):
		if not event.name.endswith(".txt"): return
		log(f"Handling create event for {event.name}...")
		if event.name in self.journals:
			log(f"New file with old file's name, ditch old journal","!")
			self.process_IN_DELETE(event)
		try:
			statres = os.stat("watched/"+event.name)
		except FileNotFoundError:
			log("File disappeared before we could stat it... somehow... ignore it.","!")
			return
		journal = uuid.uuid4().hex
		cur = db.cursor()
		cur.execute("INSERT INTO journals (uuid, path, ctime, dtime) VALUES (?, ?, ?, -1)",(journal, event.name, time.time()))
		db.commit()
		self.journals[event.name] = journal
		self.contents[event.name] = ""
		log(f"Opening journal {journal}")
	def process_IN_MODIFY(self,event):
		if not event.name.endswith(".txt"): return
		log(f"Handling modify event for {event.name}...")
		if event.name not in self.journals:
			log("Modify event for a file we don't have a journal for, create one:")
			self.process_IN_CREATE(event)
		journal = self.journals[event.name]
		count = db.execute("SELECT COUNT(*) FROM entries WHERE journal=?",[journal]).fetchone()[0]
		if count>=N: log(f"{count} entries >= {N} max entries; mergedown required","!")
		while count>=N:
			log(f"{count} entries; merging first 2 entries...")
			first_two = db.execute("SELECT rowid, delta FROM entries WHERE journal=? ORDER BY mtime ASC LIMIT 2",[journal]).fetchall()
			# rotating the oldest entry out is done by applying the first 2 patches, then diffing with the empty string
			new_first = patch(patch('',first_two[0][1]),first_two[1][1])
			new_first_delta = diff('',new_first)
			cur = db.cursor()
			cur.execute("UPDATE entries SET delta = ? WHERE rowid = ?",(new_first_delta,first_two[1][0]))
			cur.execute("DELETE FROM entries WHERE rowid = ?",[first_two[0][0]])
			db.commit()
			count = db.execute("SELECT COUNT(*) FROM entries WHERE journal=?",[journal]).fetchone()[0]
		with open('watched/'+event.name) as f: realcontent = f.read()
		delta = diff(self.contents[event.name],realcontent)
		if not delta:
			log("Empty diff; modification with no change")
			return # don't log empty diffs
		cur = db.cursor()
		cur.execute("INSERT INTO entries VALUES (?, ?, ?)",(self.journals[event.name],delta,time.time()))
		db.commit()
		log(f"Stored diff in journal {self.journals[event.name]} for file {event.name}")
		self.contents[event.name] = realcontent
	def process_IN_DELETE(self,event):
		if not event.name.endswith(".txt"): return
		log(f"Handling delete event for {event.name}...")
		if event.name not in self.journals:
			log(f"We didn't have an open journal for that file so we're good!")
			return
		log(f"Closing journal {self.journals[event.name]}")
		journal = self.journals[event.name]
		cur = db.cursor()
		cur.execute("UPDATE journals SET dtime = ? WHERE uuid = ?",[time.time(),journal])
		db.commit()
		del self.journals[event.name]
		del self.contents[event.name]

journaler = Journaler()
notifier = pyinotify.Notifier(watchman, journaler)

watchid = watchman.add_watch('watched', watchmask)
notifier.loop()
