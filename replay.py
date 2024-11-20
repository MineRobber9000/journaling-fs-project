import sqlite3, argparse, atexit, time, sys
from dmphelper import patch

db = sqlite3.connect("journal.db")
def _close_db(db):
	db.commit()
	db.close()
atexit.register(_close_db,db)

def format_time(n):
	return time.strftime('%b %d %Y %H:%M:%S',time.localtime(n))

def select(l,strfunc=lambda i,j: f"{i}) {j!r}",item=True):
	for i, j in enumerate(l, 1):
		print(strfunc(i,j))
	n = ''
	while not (n.isdigit() and (n:=int(n))>=1 and n<=len(l)):
		n = input("? ")
	return l[n-1] if item else n-1

parser = argparse.ArgumentParser()
parser.add_argument("-f","--filename",help="The name of the file.")
parser.add_argument("-u","--uuid",help="The UUID of the journal.")
args = parser.parse_args()

UUID = None
if args.uuid:
	UUID = ''.join(filter(lambda c: c in '0123456789abcdef',args.uuid.lower()))
elif args.filename:
	journals = db.execute("SELECT uuid, ctime, dtime FROM journals WHERE path = ?",[args.filename]).fetchall()
	if len(journals)==0:
		print(f"No such file {args.filename}!")
		sys.exit(1)
	if len(journals)==1:
		UUID = journals[0][0]
	else:
		print("Pick a journal:")
		UUID = select(journals, lambda i, journal: f"{i}) {journal[0]} (created {format_time(journal[1])}"+(f", deleted {format_time(journal[2])}" if journal[2]!=-1 else "")+')')[0]
else:
	parser.error("Must provide either UUID or filename!")

filename = db.execute("SELECT path FROM journals WHERE uuid = ?",[UUID]).fetchone()[0]

patchset = db.execute("SELECT delta, mtime FROM entries WHERE journal = ?",[UUID]).fetchall()
if len(patchset)==0:
	print("File is empty!")
	sys.exit(0)
content = ''
for delta, mtime in patchset:
	print(f"---\nAt {format_time(mtime)}:\n---")
	content = patch(content,delta)
	print(content,end='')
