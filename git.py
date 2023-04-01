#!/usr/bin/python3

from pathlib import Path
import subprocess
import pexpect
import time
import getpass
import keyring
import os
import subprocess

"""git python helper class - python_git:
This is a python object intended to help with pushing updating a git repository via the command line.
Capabilities:
	1. uses keystore to securely store token long-term
	2. sets up local repo with credentialStorage key 'plaintext'
		(NOTE: doesn't actually use plaintext, only creates
		token storage file before and deletes after push.
		TOKEN IS STORED IN KEYRING, User authentication will be required.)
	3. tracks current repository state (up to date, commit needed, etc) and
		keeps current with checked out branch/remote origin and other metadata.
	4. TODO: git.clone(repo_url)
	5. TODO: git.init(path)
"""


token_store_file = os.path.join(os.path.expanduser("~"), 'git_token.txt')
os.environ['GCM_PLAINTEXT_STORE_PATH'] = token_store_file


def set_gitdir():
	base_dir = os.getcwd()
	path = None
	com = f"ls -d *.git"
	try:
		path = subprocess.check_output(com, shell=True).decode().strip()
	except Exception as e:
		print(f"Error: {e}")
	if path is None:
		path = input("Enter path to repo:")
	return os.path.join(base_dir, path)


class git():
	def __init__(self, path=None, email=None, name=None, token=None, init=False, url=None, store_type='local'):
		self.test_git()
		self.store_type = store_type
		self.path = None
		self.push_needed = False
		self.commit_needed = False
		self.email = None
		self.user = None
		if path is not None:
			self.path = path
		else:
			if init:
				self.path = self.init_repo()
			elif url is not None:
				self.path = self.clone(repo_url=url)
			else:
				self.path = os.getcwd()
		if self.path is None:
			txt = "Error! No repo found, provided, or init method given (clone, url, or init"
			raise Exception(Exception, txt)
		if name is not None:
			self.name = name
			self.url = f"https://github.com/{self.email}/{self.name}.git"
		else:
			self.name = 'default'
			self.url = None
		valid, msg = self.is_repo(self.path)
		if not valid:
			raise Exception(Exception, msg)
		else:
			self.get_repo_info(self.path)
		if self.email is None:
			self.email = self.get_email()
		if token is None:
			self.token = self._environ_token()
			if self.token is None:
				self.token = self.store_token
		else:
			self.token = token
		self.token_store_file = token_store_file
		self._set_config_plaintext()

	def test_git(self):
		if not self._test_git():
			self._install_git()

	def _test_git(self):
		hasgit = subprocess.check_output("which git", shell=True).decode().strip()
		if hasgit == '':
			print("Git not installed! Installing...")
			return False
		else:
			return True


	def _install_git(self):
		com = f"sudo apt-get install -y git-all"
		try:
			subprocess.check_output(com, shell=True)
			return True
		except Exception as e:
			print("Error installing git:", e)
			return False

	def init_repo(self):
		c = input("Opening browser. Create a new repo, then press enter to continue...")
		self._browse_create_repo()
		print("This function assumes you've already added a new repo on github!")
		self.name = input("Enter repository name: (blank for None, you'll have to set this up later.)")
		self.path = os.path.join(os.getcwd(), self.name)
		if not os.path.exists(self.path):
			try:
				Path(self.path).mkdir(parents=True, exist_ok=True)
			except:
				print("Path exists! Skipping create...")
				pass
		else:
			raise Exception(Exception, f"Path already exists! ({self.path})")
		com = f"cd \"{self.path}\"; echo \"# python_git\" >> README.md; git init; git add README.md"
		ret = subprocess.check_output(com, shell=True).decode().strip()
		print(ret)
		if self.email is None:
			self.email = self.set_email()
			self.user = self.set_user()
		self.url = f"https://github.com/{self.email}/{self.name}.git"
		self._commit("First commit!")
		com = f"cd \"{self.path}\"; git branch -M main; git remote add origin https://github.com/{self.email.split('@')[0]}/{self.name}.git"
		try:
			ret = subprocess.check_output(com, shell=True).decode().strip()
			if 'src refspec master does not match any' not in ret:
				skip = False
			else:
				print("Error: ret!")
				skip = True
		except Exception as e:
			ret = e
			if 'remote origin already exists' in str(e):
				print("Appears the remote has already been set up! Skipping...")
				skip = True
			else:
				print("Error: ", e)
				ret = e
				skip = True
		if ret != '':
			print(ret)
		if not skip:
			com = f"cd \"{self.path}\"; git push -u origin main"
			ret = subprocess.check_output(com, shell=True).decode().strip()
			if ret != '':
				print(ret)
			if 'src refspec master does not match any' in ret:
				txt = f"Error: It appears your repo doesn't exist! Add to github first or correct given name ({name})..."
				raise Exception(Exception, txt)
		self.get_repo_info()
		return self.path

	def clone(self, repo_url=None):
		self.url = repo_url
		self.path = os.path.join(os.getcwd(), os.path.splitext(os.path.basename(self.url))[0])
		if repo_url is not None:
			self.url = repo_url
		ret = subprocess.check_output(f"cd \"{self.path}\"; git clone \"{self.url}\"", shell=True).decode().strip()
		self.get_repo_info()
		return self.path

	def _init(self, path=None):
		if path is not None:
			self.path = path
		ret = subprocess.check_output(f"cd \"{self.path}\"; git init", shell=True).decode().strip()
		self.get_repo_info()


	def _set_config_plaintext(self):
		com = f"cd \"{self.path}\"; git config --local credential.credentialStore plaintext"
		ret = subprocess.check_output(com, shell=True).decode().strip()
		if ret != '':
			print("Error configuring local repository credential storage:", ret)
			return False
		else:
			return True

	def get_repo_info(self, path=None):
		if path is not None:
			self.path = path
		com = f"cd \"{self.path}\"; git config --local -l"
		try:
			items = subprocess.check_output(com, shell=True).decode().strip().splitlines()
			for item in items:
				if 'repositoryformatversion' in item:
					self.repo_fmt_version = int(item.split('=')[1])
				elif 'filemode' in item:
					self.filemode = bool(item.split('=')[1].title())
				elif 'bare' in item:
					self.bare = bool(item.split('=')[1].title())
				elif 'logallrefupdates' in item:
					self.log_updates = bool(item.split('=')[1].title())
				elif 'remote.origin.url' in item:
					self.url = item.split('=')[1]
				elif 'remote.origin.fetch' in item:
					self.fetch = item.split('=')[1]
				elif 'branch.master.remote' in item:
					self.remote_branch = item.split('=')[1]
				elif 'branch.master.merge' in item:
					self.branch = item.split('=')[1]
				elif 'user.email' in item:
					self.email = item.split('=')[1]
				elif 'user.name' in item:
					self.user = item.split('=')[1]
					
		except Exception as e:
			print(e)
			self.repo_fmt_version = None
			self.filemode = None
			self.bare = None
			self.log_updates = True
			self.url = None
			self.fetch = None
			self.remote_branch = None
			self.branch = None

	def _environ_token(self):
		try:
			token = str(os.environ['GIT_TOKEN'])
			self.store_token(token=token)
		except Exception as e:
			txt = f"Error in environment variable token test:{e}"
			raise Exception(Exception, txt)
		return token


	def _set(self, key, val, store_type=None):
		if store_type is not None:
			self.store_type = store_type
		ret = True
		msg = None
		if self.store_type != 'local' and self.store_type != 'global':
			msg = f"Bad store type ({self.store_type})! Valid options are 'local' and 'global'"
			return False, msg
		com = f"cd \"{self.path}\"; git config --{self.store_type} {key} \"{val}\""
		ret = subprocess.check_output(com, shell=True).decode()
		if ret == '':
			ret = True
		else:
			msg = ret
			ret = False
		return ret, msg
		
		


	def set_email(self, email=None, store_type=None):
		if email is None:
			email = input("Enter email address for repo: {self.name}:")
		self.email = email
		if store_type is not None:
			self.store_type = store_type
		ret, msg = self._set(key="user.email", val=self.email, store_type=self.store_type)
		if not ret:
			print(f"Error setting email: {msg}!")
			return None
		else:
			return self.email

	def get_email(self):
		if self.email is not None:
			return self.email
		else:
			return self.set_email()

	def set_user(self, first_name=None, last_name=None, store_type=None):
		if first_name is None:
			first_name = input("Enter first_name:")
		if last_name is None:
			last_name = input("Enter last name:")
		self.user = f"{first_name} {last_name}"
		if store_type is not None:
			self.store_type = store_type
		ret, msg = self._set(key="user.name", val=self.email, store_type=self.store_type)
		if not ret:
			print(f"Error setting name: {msg}!")
			return None
		else:
			return self.email

	def get_email(self):
		if self.email is not None:
			return self.email
		else:
			return self.set_email()
		

	def get_config(self, key=None):
		if key is None:
			com = f"git config --global -l"
		else:
			com = f"git config --global -l | grep \"{key}\" | cut -d \'=\' -f 2"
		try:
			data = subprocess.check_output(com, shell=True).decode().strip()
			if "\n" in data:
				ret = True
				data = data.splitlines()
			elif ret == '':
				data = None
				ret = False
		except Exception as e:
			data = e
			ret = False
		if not ret:
			print(f"Error:{data}")
		return data


	def _status(self):
		self.get_repo_info()
		com = f"cd \"{self.path}\"; git status"
		return self.sh(com)


	def status(self):
		com = f"cd \"{self.path}\"; git status"
		self.get_repo_info()
		ret, data = self.sh(com)
		for line in data.splitlines():
			if 'On branch ' in line:
				self.branch = line.split('On branch ')[1]
				self.remote_branch = 'origin'
			if f"is up to date with \'{self.remote_branch}/{self.branch}\'" in line:
				self.push_needed = False
			elif 'Untracked files:' in line or 'Your branch is ahead of ' in line:
				self.push_needed = True
			if 'nothing to commit' in line or 'working tree clean' in line:
				self.commit_needed = False
			elif 'untracked files present' in line or 'Changes not staged for commit' in line:
				self.commit_needed = True
		print(f"branch:{self.branch}, self.commit_needed:{self.commit_needed}, push_needed:{self.push_needed}")

	def is_repo(self, path=None, name=None):
		if name is not None:
			self.name = name
		if path is not None:
			self.path = path
		ret, msg = self._status()
		if not ret:
			print(f"Error: Not a repository! ({ret})")
			self.init_repo()
			ret, msg = self._status()
			if not ret:
				return False, msg
			else:
				return True, None
		else:
			return True, None

	def sh(self, com):
		try:
			ret = subprocess.check_output(com, shell=True).decode().strip()
			if ret == '':
				ret = None
			return True, ret
		except Exception as e:
			ret = e
			return False, e

	def store_token(self, token=None, user=None, email=None):# user is git Name, email is git email(for login)
		if user is not None:
			self.user = user
		if email is not None:
			self.email = email
		if token is None:
			token1 = getpass.getpass("Enter git auth token: ")
			token2 = getpass.getpass("Please verify auth token: ")
			if token1 == token2:
				self.token = token1
		else:
			self.token = token
		
		keyring.set_password(service_name="git_token", username=self.email, password=self.token)
		fname = os.path.join(os.path.expanduser("~"), 'git_token.txt')
		com = f"cd \"{self.path}\"; git config --local credential.credentialStore plaintext"
		ret = subprocess.check_output(com, shell=True).decode().strip()
		if ret != '':
			print("Error storing token:", ret)
			return False
		os.environ['GCM_PLAINTEXT_STORE_PATH'] = fname
		return self.token

	def get_token(self, user=None, email=None):
		if name is not None:
			self.email = email
		if user is not None:
			self.user = user
		try:
			self.token = keyring.get_password(service_name="git_token", username=self.email)
		except Exception as e:
			print("Error getting token:", e)
			self.token = self.store_token(user=self.user, email=self.email)
		return self.token

	def _commit(self, commit_message=None):
		if commit_message is None:
			commit_message = "Default commit message (generated by git.commit(commit_message=None))."
		com = f"cd \"{self.path}\"; git add .; git commit -m \"{commit_message}\""
		try:
			ret = subprocess.check_output(com, shell=True).decode().strip()
			print(ret)
			return True
		except Exception as e:
			ret = e
			print(ret)
			return False


	def _add(self):
		com = f"cd \"{self.path}\"; git add ."
		ret = subprocess.check_output(com, shell=True).decode().strip()
		if ret == '':
			return True
		else:
			print("Error adding files:", ret)
			return False


	def _push(self, token=None, email=None, force=False):
		if token is not None:
			self.token = token
		if email is not None:
			self.email = email
		os.chdir(self.path)
		if force:
			com = "/usr/bin/git push --force"
		else:
			com = "/usr/bin/git push"
		child = pexpect.spawn(com)
		time.sleep(2)
		child.sendline(self.email)
		time.sleep(2)
		child.sendline(self.token)
		child.expect(pexpect.EOF, timeout=None)
		return child.before.decode()


	def _browse_create_repo(self):
		url = "https://github.com/new"
		ret = subprocess.check_output(f"xdg-open \"{url}\"", shell=True).decode().strip()
		if ret != '':
			print("Error openin browser:", ret)


	def _write_token_file(self, token=None, fname=None):
		if token is not None:
			self.token = token
		if fname is not None:
			self.token_store_file = fname
		try:
			with open(self.token_store_file, 'w') as f:
				f.write(self.token)
				f.close()
				return True
		except Exception as e:
			print("Couldn't write token file:", e)
			return False

	def _rm_token_file(self, fname=None):
		if fname is not None:
			self.token_store_file = fname
		com = f"rm \"{self.token_store_file}\""
		ret = subprocess.check_output(com, shell=True).decode().strip()
		if ret != '':
			print("Error removing token file:", ret)
			return False
		else:
			return True
		

	def push(self, commit_message=None, force=False):
		if not self._write_token_file():
			print("Error! Aborting...")
			return False
		self.status()
		if self.commit_needed:
			ret = self._add()
			ret = self._commit(commit_message)
			if not ret:
				raise Exception(Exception, ret)
			self.commit_needed = False
			self.push_needed = True
		if self.push_needed:
			ret = self._push(self.token, self.email)
			print(ret)
		if not self._rm_token_file():
			print(f"WARNING!!! COULD NOT DELETE TOKEN FILE AT \'{self.token_store_file}\'")
		return True


	def _pull(self):
		return subprocess.check_output(f"cd \"{self.path}\"; git pull", shell=True).decode().strip()

if __name__ == "__main__":
	url = None
	init = False
	path = None
	import sys
	try:
		func = sys.argv[1]
	except Exception as e:
		print(f"no argument provided ({e})! setting push...")
		func = "push"
	funcs = ['pull', 'add', 'push', 'status', 'new', 'commit']
	if func not in funcs:
		print(f"unknown function:{func}!")
		exit()
	try:
		arg1 = sys.argv[2]
	except:
		arg1 = None
	try:
		arg2 = sys.argv[3]
	except:
		arg2 = None
	if arg1 is not None:
		if 'http' in arg1:
			url = arg1
		elif '-u' in arg1 or '--url' in arg1:
			if arg2 is not None:
				url = arg2
			else:
				url = input("Enter url:")
		if os.path.exists(arg1):
			path = arg1
		elif '-p' in arg1 or '--path' in arg1:
			if arg2 is not None:
				path = arg2
			else:
				path = input("enter repo directory path:")
		if '-i' in arg1 or '--init' in arg1:
			init=True
	else:
		path = set_gitdir()
	print(f"func:{func}, path:{path}, url:{url}, init:{init}")
	if url is not None:
		git = git(url=url)
	elif path is not None:
		git = git(path=path)
	elif init:
		git = git(init=init)
	if func == 'add':
		print(git._add())
	elif func == 'pull':
		print(git._pull())
	elif func == 'push':
		try:
			ret = git.push()
			print("ret:", ret)
			ok = True
		except Exception as e:
			print("Couldn't push: ", e)
			ret = str(e)
			ok = False
		if '! [rejected]' in str(ret):
			ok = False
		if not ok:
			if not force:
				print(ret)
				yn = input("Remote repo has changes you don't have! Force update? (y/n)")
				if yn == 'y':
					ret = git._push(token=git.token, email=git.email, force=True)
					print(ret)
			else:
				print("Remote repo has changes you don't have! Forcing update... (force=True)")
				ret = git._push(token=git.token, email=git.email, force=True)
				print(ret)
	elif func == 'status':
		ret, data = git._status()
		print("\n".join(data.splitlines()))
	elif func == 'commit':
		if arg1 is not None:
			git._commit(arg1)
		else:
			git._commit()
