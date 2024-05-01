from datetime import datetime
import subprocess

_print = locals()['__builtins__']['print']

def print(val):
	classes = (Owner, Permissions, Created, Modified, Changed, Accessed)
	if isinstance(val, classes):
		_print(f"{val.__class__}:", val.__dict__)
	else:
		_print(val)

class Owner():
	def __init__(self, data):
		for k in data:
			v = data[k]
			self.__dict__[k] = v

class Permissions():
	def __init__(self, data):
		for k in data:
			v = data[k]
			self.__dict__[k] = v

class Created():
	def __init__(self, data):
		for k in data:
			v = data[k]
			self.__dict__[k] = v

class Modified():
	def __init__(self, data):
		for k in data:
			v = data[k]
			self.__dict__[k] = v

class Changed():
	def __init__(self, data):
		for k in data:
			v = data[k]
			self.__dict__[k] = v

class Accessed():
	def __init__(self, data):
		for k in data:
			v = data[k]
			self.__dict__[k] = v

class fileStats():
	def __init__(self, filepath='/var/storage/dev/python3/xrandr.py'):
		self.filepath = filepath
		self.owner, self.permissions, self.created, self.modified, self.changed, self.accessed = self.getStats(self.filepath)
	def sh(self, com):
		return subprocess.check_output(com, shell=True).decode().strip()
	def tsToSeconds(self, dt):
		rounded = str(round(float(f"0.{dt.split('.')[1]}"), 6)).split('.')[1]
		newdt = f"{dt.split('.')[0]}.{rounded}"
		ts = datetime.strptime(newdt, '%Y-%m-%d-%H:%M:%S.%f').timestamp()
		return ts
	def isNewer(self, target):
		OWNER, PERMISSIONS, CREATED, MODIFIED, CHANGED, ACCESSED = self.getStats(filepath=target)
		return self.modified.ts > MODIFIED.ts
	def isOlder(self, target):
		OWNER, PERMISSIONS, CREATED, MODIFIED, CHANGED, ACCESSED = self.getStats(filepath=target)
		return self.modified.ts < MODIFIED.ts
	def sameAs(self, target):
		OWNER, PERMISSIONS, CREATED, MODIFIED, CHANGED, ACCESSED = self.getStats(filepath=target)
		return self.modified.ts == MODIFIED.ts
	def compare(self, target):
		if self.isNewer(target):
			ret = 'Newer'
		elif self.isOlder(target):
			ret = 'Older'
		elif self.sameAs(target):
			ret = 'Same'
		return ret
	def getStats(self, filepath=None):
		if filepath is None:
			filepath = self.filepath
		out = {}
		data = self.sh(f"stat \"{filepath}\"")
		owner = {}
		owner['user_id'] = data.split('Uid: ( ')[1].split('/')[0]
		owner['user_name'] = data.split('Uid: ( ')[1].split('/')[1].split(')')[0].strip()
		owner['group_id'] = data.split('Gid: ( ')[1].split('/')[0]
		owner['group_name'] = data.split('Gid: ( ')[1].split('/')[1].split(')')[0].strip()
		OWNER = Owner(owner)
		chunks = data.split('Uid:')[0].splitlines()
		permissions = {}
		permissions['numeric'] = chunks[len(chunks) - 1].split('(')[1].split('/')[0]
		permissions['ascii'] = chunks[len(chunks) - 1].split('(')[1].split('/')[1].split(')')[0]
		PERMISSIONS = Permissions(permissions)
		created = {}
		modified = {}
		changed = {}
		accessed = {}
		chunks = data.splitlines()
		created['date'], created['time'] = chunks[len(chunks) - 1].split(': ')[1].split(' -')[0].split(' ')
		created['strptime'] = f"{created['date']}-{created['time']}"
		created['ts'] = self.tsToSeconds(created['strptime'])
		CREATED = Created(created)
		modified['date'], modified['time'] = chunks[len(chunks) - 3].split(': ')[1].split(' -')[0].split(' ')
		modified['strptime'] = f"{modified['date']}-{modified['time']}"
		modified['ts'] = self.tsToSeconds(modified['strptime'])
		MODIFIED = Modified(modified)
		changed['date'], changed['time'] = chunks[len(chunks) - 2].split(': ')[1].split(' -')[0].split(' ')
		changed['strptime'] = f"{changed['date']}-{changed['time']}"
		changed['ts'] = self.tsToSeconds(changed['strptime'])
		CHANGED = Changed(changed)
		accessed['date'], accessed['time'] = chunks[len(chunks) - 4].split(': ')[1].split(' -')[0].split(' ')
		accessed['strptime'] = f"{accessed['date']}-{accessed['time']}"
		accessed['ts'] = self.tsToSeconds(accessed['strptime'])
		ACCESSED = Accessed(accessed)
		return OWNER, PERMISSIONS, CREATED, MODIFIED, CHANGED, ACCESSED

class testFiles():
	def __init__(self, file1=None, file2=None):
		self.filepath_1 = file1
		self.filepath_2 = file2
		self.FILE_1 = fileStats(self.filepath_1)
		self.FILE_2 = fileStats(self.filepath_2)
	def isNewer(self):
		if self.FILE_1.created.ts > self.FILE_2.created.ts:
			pass
