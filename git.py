#!/usr/bin/python3

import pickle
from helper_utils.filesystem import filesystem
from pathlib import Path
import subprocess
import pexpect
import time
import getpass
import keyring
import os
import requests

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
	4. Allows creation of 'to_merge' (or other name) branch to protect changes in 'main'.
	5. TODO: merge secondary branch to main
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


def _get_repositories_html(user='darthmonkey2004'):
	url = f"https://github.com/{user}?tab=repositories"
	r = requests.get(url)
	if r.status_code != 200:
		print(f"Error: Bad status ({r.status_code}, {r.text})!")
		return None
	else:
		return r.text

def get_repositories(user='darthmonkey2004'):
	html = _get_repositories_html(user)
	s = '<ul data-filterable-for=\"your-repos-filter\" data-filterable-type=\"substring\">'
	d = html.split(s)[1].split('</ul>')[0]
	items = d.strip().split('<li')
	data = {}
	for item in items:
		if item != '':
			item = item.split('<a href="')[1]
			path = item.split('"')[0]
			_type = item.split(path)[1].split('itemprop="name ')[1].split('"')[0]
			name = item.split(_type)[1].split('>')[1].strip().split('</a')[0]
			try:
				description = item.split('itemprop=\"description\">')[1].split('</p>')[0].strip()
			except:
				description = "No description provided!"
			try:
				lang = item.split('itemprop=\"programmingLanguage\">')[1].split('<')[0]
			except:
				lang = None
			try:
				license = item.split('</svg>')[1].split('<')[0].strip()
			except:
				license = None
			updated_timestamp = item.split('Updated <relative-time datetime=\"')[1].split('"')[0]
			updated_string = item.split(updated_timestamp)[1].split('>')[1].split('<')[0]
			data[name] = {}
			data[name]['path'] = path
			data[name]['description'] = description
			data[name]['repo_type'] = _type
			data[name]['programming_language'] = lang
			data[name]['license'] = license
			data[name]['updated'] = {}
			data[name]['updated']['timestamp'] = updated_timestamp
			data[name]['updated']['string'] = updated_string
	return data


class git_mgr():
	def __init__(self, path=None, url=None, init=False, email=None, name=None, token=None, store_type='local', update=True, safe=True):
		self.settings = None
		self.safe = safe
		if path is None and url is None:
			self.settings = self.load_settings()
			os.chdir(self.path)
		self.update = update
		self.update_needed = False
		self.test_git()
		self.store_type = store_type
		self.path = None
		self.push_needed = False
		self.commit_needed = False
		self.email = None
		self.user = None
		self.fs = filesystem()
		if path is not None:
			self.path = path
		else:
			if init:
				self.path = self.new_repo()
			elif url is not None:
				self.path = self.clone(repo_url=url)
			else:
				self.path = os.getcwd()
		if self.path is None:
			txt = "Error! No repo found, provided, or init method given (clone, url, or init"
			raise Exception(Exception, txt)
		else:
			os.chdir(self.path)
		if name is not None:
			self.name = name
		else:
			self.name = os.path.basename(self.path)
		self.url = f"https://github.com/{self.email}/{self.name}.git"
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
		self.commit_needed, self.push_needed = self.status()
		if self.commit_needed or self.push_needed:
			print("Your local branch is ahead of remote! (Update with git.push())")
		if self.settings is None:
			self.save_settings()
		if self.user is None:
			self.user = self.email.split('@')[0]

	def del_branch(self, branch=None, safe=None):
		if safe is None:
			safe = self.safe
		go = False
		if branch is None:
			txt = f"Error deleting branch: No branch specified for removal!"
			raise Exception(txt)
		if safe:
			print("Safety check is on! You are about to delete branch {branch}!")
			yn = input("Are you sure? (y/n)")
			if yn == 'y':
				go = True
			else:
				print("Aborting delete...")
				go = False
				return go
		else:
			go = True
		if go:
			ret, msg = self.sh(f"git branch -d {branch}")
			if ret:
				print(f"Successfully deleted branch: {branch}!")
				return True
			else:
				print("Error deleting branch - {msg}!")
				return False
				

	def _save_settings(self, settings=None, settings_file=None):
		if settings is None:
			self.settings = {}
		else:	
			self.settings = settings
		if settings_file is None:
			path = os.path.join(os.path.expanduser("~"), '.helper_utils', 'git')
			settings_file = os.path.join(path, 'settings.dat')
		else:
			path = os.path.dirname(settings_file)
		if not os.path.exists(path):
			print("Home git settings directory doesn't exist! Creating...")
			self.fs.mkdir(path)
		try:
			with open(settings_file, 'wb') as f:
				pickle.dump(self.settings, f)
				f.close()
			return True
		except Exception as e:
			txt = "Error saving settings:{e}"
			raise Exception(txt)


	def save_settings(self, settings_file=None):
		if settings_file is not None:
			self.settings_file = settings_file
		else:
			path = os.path.join(os.path.expanduser("~"), '.helper_utils', 'git')
			self.settings_file = os.path.join(path, 'settings.dat')
		vars = ['bare', 'branch', 'commit_needed', 'email', 'fetch', 'filemode', 'fs', 'name', 'path', 'remote_branch', 'repo_fmt_version', 'token_store_file', 'url', 'user']
		d = {}
		for var in vars:
			d[var] = self.__dict__[var]
		self._save_settings(settings=d, settings_file=self.settings_file)
		return self.settings

	def load_settings(self, settings_file=None):
		if settings_file is not None:
			self.settings_file = settings_file
		try:
			self.settings = self._load_settings(settings_file=settings_file)
			for k in self.settings.keys():
				self.__dict__[k] = self.settings[k]
			print("Settings loaded successfully!")
			return self.settings
		except Exception as e:
			txt = f"Error loading settings: {e}"
			raise Exception(txt)

	
	def _load_settings(self, settings_file=None):		
		if settings_file is None:
			path = os.path.join(os.path.expanduser("~"), '.helper_utils', 'git')
			settings_file = os.path.join(path, 'settings.dat')
		else:
			path = os.path.dirname(settings_file)
		if not os.path.exists(settings_file):
			print("Git settings file not found! Creating...")
			self.save_settings(settings_file=settings_file)
		try:
			with open(settings_file, 'rb') as f:
				self.settings = pickle.load(f)
				f.close()
			return self.settings
		except Exception as e:
			txt = f"Error loading settings:{e}"
			print(txt)
			return self.save_settings(settings_file=settings_file)
			
	def get_current_branch(self):
		ret, msg = self.sh("git branch --show-current")
		if not ret:
			print(f"Error getting current branch: {ret}")
			return ret
		else:
			self.branch = msg
		return self.branch

	def get_merge_sources(self, branch=None):
		if branch is not None:
			self.set_branch(branch=branch)
		ret, data = self.sh("git ls-remote")
		if ret:
			heads = []
			pulls = []
			refs = {}
			data = data.splitlines()
			for line in data:
				if 'HEAD' in line:
					sha = line.split("\t")[0]
					refs[sha] = {}
					refs[sha]['name'] = 'HEAD'
					refs[sha]['path'] = 'HEAD'
				if 'refs/heads/' in line:
					sha = line.split("\t")[0]
					refs[sha] = {}
					refs[sha]['name'] = line.split('refs/heads/')[1]
					refs[sha]['path'] = f"refs/heads/{refs[sha]['name']}"
				if 'refs/pull/' in line:
					sha = line.split("\t")[0]
					_id = line.split('refs/pull/')[1].split('/')[0]
					name = line.split(f"refs/pull/{_id}/")[1]
					refs[sha] = {}
					refs[sha]['name'] = name
					refs[sha]['id'] = _id
					refs[sha]['path'] = f"refs/pull/{_id}/{name}"
		self.merge_sources = refs
		return self.merge_sources

	def create_branch(self, branch):
		ret, msg = self.sh(f"git branch {branch}")
		if ret:
			ret, msg = self.set_branch(branch=branch)
		return ret, msg



	def set_branch(self, branch=None, create=False):
		if branch is not None:
			self.branch = branch
		else:
			self.branch = 'main'
		if not create:# if force create isn't set...
			if self.branch not in self.get_remote_branches():#if branch doesn't exist...
				print("Remote branch not found! Setting create flag...")
				create = True
			else:
				create = False
		if create:#if either branch doesn't exist or force create flag set...
			ret, msg = self.create_branch(self.branch)
			if ret:
				pass
			else:
				print(f"Error creating branch!")
		else:#if create not needed...
			ret, msg = self.sh(f"git checkout {branch}")#switch to branch
			if ret:
				pass
			else:
				print(f"Error setting branch!")
		return self.branch

	def pull_branch(self, branch):
		ret, msg  = self.sh(f"git pull origin {branch}")
		if not ret:
			print("Error getting existing branch {branch}: {msg}")
			return ret
		self.set_branch(branch=branch)
		return True


	def create_new_fromBranch(self, new_branch, src_branch):
		ret, msg = self.sh(f"git checkout -b {new_branch} {src_branch}")
		if not ret:
			print(f"Error creating branch {new_branch} from {src_branch}: {msg}")
			return ret
		self.set_branch(branch=new_branch)
		return True


	def get_last_commit(self, branch=None):
		if branch is None:
			branch = self.branch
		return self.get_commit_history(branch=branch, return_last=True)

	def get_last_commitId(self, branch=None):
		return self.get_commit_history(branch=branch, return_last=True)['sha']

	def get_commit_history(self, branch=None, return_last=False):
		if branch is None:
			branch = self.branch
		ret, data = self.sh('git log')
		if not ret:
			print("Error getting commit history -", ret)
			return {}
		data = data.splitlines()
		out = {}
		desc = None
		for line in data:
			if "commit " in line and "commit message" not in line:
				new = True
				sha = line.split("commit ")[1]
				out[sha] = {}
				d = out[sha]
				d['sha'] = sha
			else:
				new = False
			if "commit message" in line:
				d['commit_message'] = line.split("commit message ")[1]
			elif "Merge: " in line:
				d['merge'] = line.split("Merge: ")[1]
			elif "Author: " in line:
				d['author'] = line.split('Author: ')[1]
			elif "Date: " in line:
				d['date'] = line.split('Date:')[1].strip()
			else:
				if line != '':
					if not new:
						desc.append(line.strip())
					elif new:
						if desc is None:
							desc = []
							d['description'] = None
						else:
							d['description'] = ". ".join(desc)
							desc = []
		for sha in out.keys():
			d = out[sha]['description']
			if d == '':
				out[sha]['description'] = None
		self.commits = out
		if not return_last:
			return self.commits
		else:
			sha = list(self.commits.keys())[0]
			return self.commits[sha]


	def _merge(self, merge_from, merge_to='main'):
		un, pn = self.status()
		if un:
			self._commit(f"Merging {merge_from} to {merge_to}.")
		self.set_branch(merge_to)
		ret, msg = self.sh(f"git merge {merge_from}")
		if ret:
			ret, msg = self.sh(f"git push --set-upstream origin {branch}")
			if not ret:
				print("Error pushing to remote repo - {ret}")
				return False
			else:
				return True, None
		else:
			print(f"Error in merge: {msg}!")
			return False, msg

	def merge(self, merge_from, merge_to='main'):
		remotes = self.get_remote_branches()
		if merge_from not in remotes:
			print(f"Error - repo {merge_from} not in remote branches!")
			return False
		if merge_to not in remotes:
			print(f"Error - repo {merge_to} not in remote branches!")
			return False
		ret, msg = self._merge(merge_from=merge_from, merge_to=merge_to)
		if not ret:
			raise Exception(msg)
		else:
			return


	def merge_main_to_branch(self, target_branch):
		self.set_branch(branch=target_branch)
		ret, msg = self.sh("git merge main")
		if not ret:
			print("Error merging main into branch {target_branch}: {ret}")
			return ret
		else:
			return True


	def get_repositories(self):
		user = self.email.split('@')[0]
		self.repositories = get_repositories(user)
		return self.repositories

	def get_remote_branches(self):
		ret, remotes = self.sh(f"git branch --remotes")
		if ret:
			remotes = remotes.splitlines()
			l = []
			for r in remotes:
				l.append(r.split('/')[1].strip())
			self.remotes = l
		else:
			print("Failed to get remote branches:", ret)
			self.remotes = ['main']
		return self.remotes

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

	def new_repo(self, name=None, path=None):
		c = input("Opening browser. Create a new repo, then press enter to continue...")
		self._browse_create_repo()
		print("This function assumes you've already added a new repo on github!")
		if path is None:
			if name is None:
				self.name = input("Enter repository name: (blank for None, you'll have to set this up later.)")
			else:
				self.name = name
			self.path = os.path.join(os.getcwd(), self.name)
		else:
			self.path = path
			self.name = os.path.basename(self.path)
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
			if self.branch == 'main':
				print("WARNING: Updating main branch! Highly suggested to create a new branch (self.set_branch)...")
			com = f"cd \"{self.path}\"; git push -u origin {self.branch}"
			ret = subprocess.check_output(com, shell=True).decode().strip()
			if ret != '':
				print(ret)
			if 'src refspec master does not match any' in ret:
				txt = f"Error: It appears your repo doesn't exist! Add to github first or correct given name ({name})..."
				raise Exception(Exception, txt)
		self.get_repo_info()
		return self.path

	def clone(self, repo_url=None):
		if repo_url is not None:
			self.url = repo_url
		repo_name = os.path.splitext(os.path.basename(repo_url))[0]
		if repo_name in os.getcwd():
			self.path = os.getcwd()
			createin = os.path.dirname(self.path)
		else:
			self.path = os.path.join(os.getcwd(), repo_name)
			createin = os.getcwd()
		os.chdir(createin)
		ret = subprocess.check_output(f"cd \"{self.path}\"; git clone \"{self.url}\"", shell=True).decode().strip()
		os.chdir(self.path)
		self.get_repo_info()
		return self.path

	def _init(self, path=None):
		if path is not None:
			self.path = path
			os.chdir(self.path)
		ret = subprocess.check_output(f"git init", shell=True).decode().strip()
		self.get_repo_info()


	def _set_config_plaintext(self):
		com = f"git config --local credential.credentialStore plaintext"
		ret = subprocess.check_output(com, shell=True).decode().strip()
		if ret != '':
			print("Error configuring local repository credential storage:", ret)
			return False
		else:
			return True

	def get_repo_info(self, path=None):
		if path is None:
			path = self.path
		com = f"cd \"{path}\"; git config --local -l"
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
					self.branch = self.get_current_branch()
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
			self.branch = self.get_current_branch()

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


	def status(self, update=None):
		if update is not None:
			self.update = update
		if self.update:
			com = f"cd \"{self.path}\"; git fetch origin"
			ret, data = self.sh(com)
		com = f"cd \"{self.path}\"; git status"
		self.get_repo_info()
		ret, data = self.sh(com)
		for line in data.splitlines():
			if 'On branch ' in line:
				self.branch = self.get_current_branch()
				self.remote_branch = 'origin'
			if f"is up to date with \'{self.remote_branch}/{self.branch}\'" in line:
				self.push_needed = False
			elif 'Untracked files:' in line or 'Your branch is ahead of ' in line:
				self.push_needed = True
			if 'nothing to commit' in line or 'working tree clean' in line:
				self.commit_needed = False
			elif 'untracked files present' in line or 'Changes not staged for commit' in line:
				self.commit_needed = True
			elif 'Your branch is behind' in line:
				if self.update:
					print("Local repository needs updated! Updating now... (update=True)")
					self._pull()
		print(f"branch:{self.branch}, self.commit_needed:{self.commit_needed}, push_needed:{self.push_needed}")
		return self.commit_needed, self.push_needed

	def is_repo(self, path=None, name=None):
		if name is not None:
			self.name = name
		if path is not None:
			self.path = path
		ret, msg = self._status()
		if not ret:
			print(f"Error: Not a repository! ({ret})")
			self.new_repo()
			ret, msg = self._status()
			if not ret:
				return False, msg
			else:
				return True, None
		else:
			return True, None

	def sh(self, com):
		if 'git' not in com:# restrict shell commands to contain the 'git' command in string.
			txt = f"Error - invalid git string: {com}"
			raise Exception(txt)
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
	

	def list_commands(self, command='all'):
		function_data = {'all': 'get_config(key=None)# if None, get all config variables in git directory (unless global, then system wide)', 'del_branch': 'del_branch(branch=None, safe=None)', 'save_settings': 'save_settings(settings_file=None)', 'load_settings': 'load_settings(settings_file=None)', 'get_current_branch': 'get_current_branch()', 'get_merge_sources': 'get_merge_sources(branch=None)', 'create_branch': 'create_branch(branch)', 'set_branch': 'set_branch(branch=None, create=False)', 'push': 'push(commit_message=None, force=False)', 'pull': 'pull()', 'pull_branch': 'pull_branch(branch)', 'create_new_fromBranch': 'create_new_fromBranch(new_branch, src_branch)', 'get_last_commit': 'get_last_commit(branch=None)', 'get_last_commitId': 'get_last_commitId(branch=None)', 'get_commit_history': 'get_commit_history(branch=None, return_last=False)', 'merge': 'get_merge_sources(branch=None)', 'merge_main_to_branch': 'merge_main_to_branch(target_branch)', 'get_repositories': 'get_repositories()', 'get_remote_branches': 'get_remote_branches()', 'new_repo': 'new_repo()', 'close': 'new_repo()', 'get_repo_info': 'get_repo_info(path=None)', 'set_email': "set_email(email=None, store_type=None)# store_type defaults=['local', 'global']", 'get_email': 'get_email()', 'set_user': 'set_user(first_name=None, last_name=None, store_type=None)', 'get_config': 'get_config(key=None)# if None, get all config variables in git directory (unless global, then system wide)', 'status': "status(update=None)# if update=True, will do a pull on the current repo to ensure it's up to date.", 'is_repo': 'is_repo(path=None, name=None)', 'store_token': 'store_token(token=None, user=None, email=None)', 'get_token': 'get_token(user=None, email=None)'}
		flist = list(function_data.keys())
		l = []
		if command in flist:
			if command == 'all':
				del function_data['all']
				for k in function_data.keys():
					l.append(f"{k} - {function_data[k]}")
			else:
				l.append(f"{k} - {function_data[command]}")
		return "\n".join(l)

	def rm_junk_files(self):
		paths = self.fs.find(path=self.path, pattern="__pycache__")
		for path in paths:
			try:
				self.fs.rm(path)
			except Exception as e:
				log(f"git.rm_junk_files():Error - {e}", 'error')
				return False
		return True


	def push(self, commit_message=None, force=False):
		self.rm_junk_files()
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


	def pull(self):
		return subprocess.check_output(f"git pull", shell=True).decode().strip()

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
