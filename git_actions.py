from helper_utils import sh

sh = sh.shell().sh

"""revisions:
diff: Show changes between commits, commit and working tree, etc
grep: Print lines matching a pattern
log: Show commit logs
show: Show various types of objects
status: Show the working tree status
"""

def fetch():
	return sh("git fetch")

def pull():
	return sh("git pull")

def push():
	return sh("git push")

def init(path):
	return sh(f"cd \"{path}\"; git init")

def add(files=[]):
	if files == []:
		files = '.'
	else:
		files = ",".join(files)
	com = f"git add \"{files}\""
	return sh(com)

def mv(src, dest):
	com = f"git mv \"{src}\" \"{dest}\""
	return sh(com)

def rm(files=[]):
	if files == []:
		files = '.'
	else:
		files = ",".join(files)
	com = f"git rm \"{files}\""
	return sh(com)

def restore(files=[]):
	if files == []:
		files = '.'
	else:
		files = ",".join(files)
	com = f"git restore \"{files}\""
	return sh(com)

def clone(repo_url, repopath=None):
	if repopath is None:
		repopath = os.getcwd()
	dirname = os.path.basename(repopath)
	path = os.path.dirname(repopath)
	com = f"cd \"{path}\"; git clone \"{repo_url}\""
	ret = sh(com)
	if os.path.exists(repopath):
		return True
	else:
		return False

def log():
	return sh("git log")

def show():
	return sh("git show")

def merge():
	return sh("git merge")

def commit(message='default commit mesage'):
	return sh(f"git commit -m \"{message}\"")

def rebase():
	ret = sh("git rebase")
	if 'error: cannot rebase:' in ret:
		print(f"Error - {ret}")
		return False
	else:
		return True

def addTag(tag_name):
	return sh(f"git tag \"{tag_name}\"")

def listTags():
	return sh(f"git tag -l")

def rmTag(tag_name):
	return sh(f"git tag -d \"{tag_name}\"")

def newFile(filepath, branch_name='edits'):
	newBranch(branch_name)

def reset():
	return sh("git reset")

def getBranch():
	return sh("git branch")

def newBranch(branch_name):
	return sh(f"git checkout -b \"{branch_name}\"")

def checkout(branch_name):
	return sh(f"git checkout \"{branch_name}\"")

def switch(branch_name):
	return sh(f"git switch \"{branch_name}\"")

def commit(message='Default commit message.'):
	return sh(f"git commit -a -m \"{message}\"")

def bisect(action):
	actions = ['help', 'start', 'bad', 'good', 'new', 'old', 'terms', 'skip', 'next', 'reset', 'visualize', 'view', 'replay', 'log', 'run']
	print("TODO - bisect: Use binary search to find the commit that introduced a bug")

def diff():
	return sh("git diff")

def grep(query):
	return sh(f"git grep \"{query}\"")

def log():
	return sh("git log")

def show():
	return sh("git show")

def status():
	return sh("git status")
