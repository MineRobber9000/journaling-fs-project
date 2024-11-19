import sqlite3, argparse, atexit, time, sys
from dmphelper import patch

db = sqlite3.connect("journal.db")
def _close_db(db):
	db.commit()
	db.close()
atexit.register(_close_db,db)

def format_time(n):
	return time.strftime('%b %d %Y %H:%M:%S',time.localtime(n))

parser = argparse.ArgumentParser()
parser.add_argument("-f","--filename",help="The name of the file.")
parser.add_argument("-u","--uuid",help="The UUID of the journal.")
args = parser.parse_args()

UUID = None
if args.uuid:
	UUID = ''.join(filter(lambda c: c in '0123456789abcdef',args.uuid.lower()))
elif args.filename:
	journals = db.execute("SELECT uuid, ctime, dtime FROM journals WHERE path = ?",[args.filename]).fetchall()
	if len(journals)==1:
		UUID = journals[0][0]
	else:
		for i, journal in enumerate(journals,1):
			print(f"{i}) {journal[0]} (created {format_time(journal[1])}",end='')
			if journal[2]!=-1:
				print(f", deleted {format_time(journal[2])}",end='')
			print(')')
		n = ''
		while not (n.isdigit() and (n:=int(n))>=1 and n<=len(journals)):
			n = input("? ")
		UUID = journals[n-1][0]
else:
	parser.error("Must provide either UUID or filename!")

filename = db.execute("SELECT path FROM journals WHERE uuid = ?",[UUID]).fetchone()[0]

patchset = db.execute("SELECT delta, mtime FROM entries WHERE journal = ?",[UUID]).fetchall()
if len(patchset)==0:
	print("File is empty!")
	sys.exit(0)
content = ''
for delta, mtime in patchset:
	print(f"{filename}, as it existed {format_time(mtime)}:\n---")
	content = patch(content,delta)
	print(content)
