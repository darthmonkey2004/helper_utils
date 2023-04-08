import errno
import os
import subprocess
import shutil
from helper_utils.log import *
logger = logger(verbose=True)
log = logger.log_msg

class filesystem():
	def __init__(self, cwd=None, overwrite=False):
		self.overwrite = overwrite
		if cwd is None:
			self.cwd = os.getcwd()
		else:
			self.cwd = cwd

	def copy(self, src_path, dest_path, overwrite=None):
		if overwrite is None:
			overwrite = self.overwrite
		if os.path.isdir(src_path):	
			self._copy_path(src_path=src_path, dest_path=dest_path, overwrite=overwrite)
			log(f"filesystem.copy():Copied contents of '{src_path}' to '{dest_path}'!", 'info')
		elif os.path.isfile(src_path):
			log(f"filesystem.copy():Copied '{src_path}' to '{dest_path}'!", 'info')
			self._copy_file(src_path=src_path, dest_path=dest_path, overwrite=overwrite)
		elif not os.path.exists(src_path):
			txt = f"filesystem.copy():Error! Source file doesn't exist! (file='{src_path}')"
			raise FileNotFoundError(txt)

	def is_empty(self, path):
		if not os.path.exists(path):
			txt = f"filesystem.is_empty():Error! Directory doesn't exist! (path='{path}')"
			raise FileNotFoundError(txt)
		if not os.path.isdir(path):
			txt = f"filesystem.is_empty():Error! Provided path is NOT a directory! (path='{path}')"
			log(txt, 'error')
			raise NotADirectoryError(txt)
		files = os.listdir(path)
		if len(files) == 0:
			return True
		else:
			return False

	def _copy_path(self, src_path, dest_path, overwrite):
		ok = False
		exists = os.path.exists(dest_path)
		if exists and not overwrite:
			txt = f"filesystem._copy_path():Error! Destination directory already exists! (dest='{dest_path}')"
			log(txt, 'error')
			raise Exception(txt)
		elif exists and overwrite:
			ok = True
		elif not exists:
			ok = True
		if ok:
			shutil.copytree(src_path, dest_path)
			return
			

	def _copy_file(self, src_path, dest_path, overwrite):
		exists = os.path.exists(dest_path)
		if exists and not overwrite:
			txt = f"filesystem._copy_path():Error! Destination file already exists! (dest='{dest_path}')"
			log(txt, 'error')
			raise Exception(txt)
		elif exists and overwrite:
			ok = True
		elif not exists:
			ok = True
		if ok:
			shutil.copy2(src_path, dest_path)

	def _rm_dir(self, path, force=False):
		is_empty = False
		try:
			is_empty = self.is_empty(path)
		except Exception as e:
			txt = f"filesystem._rm_dir():Error testing directory: {e}"
			log(txt, 'error')
			raise Exception(txt)
		exists = os.path.exists(path)
		is_dir = os.path.isdir(path)
		if exists and is_dir and is_empty:
			os.rmdir(path)
			log(f"filesystem._rm_dir():Removed directory: {path}!", 'info')
		elif is_dir and not is_empty and not force:
			txt = f"filesystem._rm_dir():Error - Directory not empty! (path='{path}') - Using subprocess..."
			log(txt, 'error')
			try:
				subprocess.call(f"rm -rf \"{path}\"")
			except Exception as e:
				txt = f"{txt} - {e}"
				raise Exception(txt)
		elif is_dir and not is_empty and force:
			log(f"filesystem._rm_dir():Directory not empty! Removing directory contents.. (force=True)", 'warning')
			files = self.ls(path)
			for filepath in files:
				log(f"filesystem._rm_dir():Removing file - {filepath}", 'info')
				self._rm_file(filepath)
			os.rmdir(path)

	def _rm_file(self, path):
		if os.path.exists(path):
			os.remove(path)
			log(f"filesystem._rm_file():Removed file - '{path}'!", 'info')
		else:
			raise FileNotFoundError(txt)

	def rm(self, path, force=False):
		if os.path.isdir(path):
			self._rm_dir(path, force=force)
		else:
			self._rm_file(path)

	def ls(self, path):
		if not os.path.exists(path):
			txt = f"filesystem.ls():Error - path doesn't exist! ({path})"
			log(txt, 'error')
			raise FileNotFoundError(txt)
		l = []
		for root, dirs, files in os.walk(os.path.abspath(path)):
			for filepath in files:
				l.append(os.path.join(root, filepath))
		return l


	def mkdir(self, path):
		if not os.path.exists(path):
			os.makedirs(path)
			log(f"filesystem.copy():Directory created! ({path})", 'info')
		else:
			log(f"filesystem.copy():WARNING - Directory already exists!", 'warning')


	def _mv_dir(self, src_path, dest_path):
		self.mkdir(dest_path)
		files = self.ls(src_path)
		print(files)
		ok = False
		for filepath in files:
			destpath = os.path.join(dest_path, os.path.basename(filepath))
			self.copy(filepath, destpath)
			if not os.path.exists(destpath):
				txt = f"filesystem._mv_dir():Error - file failed to copy! ({filepath})"
				log(txt, 'error')
				raise Exception(txt, filepath)
			else:
				self.rm(filepath)
				ok = True
		if ok:
			self.rm(src_path)
		log(f"filesystem.copy():Moved '{src_path}' to '{dest_path}'!", 'info')

	def _mv_file(self, src_path, dest_path):
		self.copy(src_path, dest_path)
		if not os.path.exists(dest_path):
			txt = f"filesystem._mv_dir():Error - file failed to copy! ({src_path})"
			log(txt, 'error')
			raise Exception(txt, src_path)
		else:
			self.rm(src_path)
			ok = True
		log(f"filesystem.copy():Moved '{src_path}' to '{dest_path}'!", 'info')

	def mv(self, src_path, dest_path):
		exists = os.path.exists(src_path)
		if not exists:
			txt = f"filesystem.copy():Error - path doesn't exist ({src_path})!"
			log(txt, 'error')
			raise FileNotFoundError(txt)
		if os.path.isdir(src_path):
			self._mv_dir(src_path, dest_path)
		elif os.path.isfile(src_path):
			self._mv_file(src_path, dest_path)

	def touch(self, filepath, create_dirs=True):
		path = os.path.dirname(filepath)
		if not os.path.exists(path) and create_dirs:
			log(f"filesystem.touch():Path doesn't exist! Creating...", 'warning')
			self.mkdir(path)
		with open(filepath, 'w') as f:
			data = ''
			f.write(data)
			f.close()

	def write(self, data, filepath, force=False):
		go = False
		if os.path.exists(filepath):
			if force:
				txt = f"filesystem.write():Error - File Exists! (use force=True to overwrite!)"
				go = True
			else:
				txt = None
				go = False
		else:
			go = True
		if go:
			try:
				with open(filepath, 'w') as f:
					f.write(data)
					f.close()
				return True
			except Exception as e:
				txt = f"filesystem.write():Error - {e}"
				log(txt, 'error')
				return False
		else:
			log(txt, 'error')
			return False

	def find(self, path=None, pattern="*.*"):
		self.pattern = pattern
		if path is None:
			path = self.cwd
		try:
			return subprocess.check_output(f"find \"{path}\" -name \"{pattern}\"", shell=True).decode().strip().splitlines()
		except Exception as e:
			txt = f"filesystem.find():Error - {e}"
			log(txt, 'error')
			return []
			
