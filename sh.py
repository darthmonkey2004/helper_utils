import os
import subprocess

class shell():
	def __init__(self, com=None, sudo=False):
		self.SUDO = sudo
		self.USER = self.getUser()
		self.HOME = self.get_home()
		self.COMMAND = com
		if self.COMMAND is not None:
			self.RESULTS = self.execute(self.COMMAND)
		else:
			self.RESULTS = None

	def getUser(self):
		return os.environ['USER']

	def getcwd(self):
		return os.getcwd()

	def get_home(self):
		return os.environ['HOME']

	def sh(self, com):
		if self.SUDO:
			com = f"sudo {com}"
		out = subprocess.check_output(com, shell=True).decode().strip()
		if "\n" in out:
			return out.splitlines()
		else:
			return out
		
