#!/home/khuxkm/project/venv/bin/python3
import pyinotify, uuid

watchman = pyinotify.WatchManager()
watchmask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_DELETE

def log(msg,c="*"):
	print(f"[{c}] {msg}")

class Journaler(pyinotify.ProcessEvent):
	def __init__(self):
		super(Journaler, self).__init__()
		self.journals = {}
	def process_IN_CREATE(self,event):
		if event.name.endswith(".swp"): return # don't even log it
		if not event.name.endswith(".txt"):
			log(f"We handle text files, not {event.name.rsplit('.',1)[1]} files")
			return
		log(f"Handling create event for {event.name}...")
		if event.name in self.journals:
			log(f"New file with old file's name, ditch old journal","!")
			del self.journals[event.name]
		journal = f"journal/{event.name.replace('.','_')}_{uuid.uuid4().hex}.dat"
		with open(journal,"w") as f: pass
		self.journals[event.name] = journal
	def process_IN_MODIFY(self,event):
		if event.name.endswith(".swp"): return # don't even log it
		log(f"TODO: handle modify events ({event.name})","!")
	def process_IN_DELETE(self,event):
		if event.name.endswith(".swp"): return # don't even log it
		log(f"Handling delete event for {event.name}...")
		if event.name not in self.journals:
			log(f"We didn't have an open journal for that file so we're good!")
			return
		log(f"Closing journal {self.journals[event.name]}")
		del self.journals[event.name]

journaler = Journaler()
notifier = pyinotify.Notifier(watchman, journaler)

watchid = watchman.add_watch('watched', watchmask)
notifier.loop()
