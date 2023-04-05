import subprocess
import tarfile
import glob
import os
from log import logger
logfile = os.path.join(os.path.expanduser("~"), 'new_project_helper.log')
logger = logger(logfile=logfile, verbose=True)
log = logger.log_msg

"""Helper class for managing repository backups.

Support all filetypes used by tarfile module.
Allows adding single file, multiple files (entire directory), and extraction to destination directory."""


modes_by_name = {'read - transparent compression': 'r', 'read - no compression': 'r:', 'read - gzip': 'r:gz', 'read - bzip2': 'r:bz2', 'read - lzma': 'r:xz', 'create - no compression': 'x:', 'create - gzip': 'x:gz', 'create - bzip2': 'x:bz2', 'create - lzma': 'x:xz', 'append - no compression': 'a:', 'write - no compression': 'w:', 'write - gzip': 'w:gz', 'write - bzip': 'w:bz2', 'write - lzma': 'w:xz'}
modes_by_string = {'r': 'read - transparent compression', 'r:': 'read - no compression', 'r:gz': 'read - gzip', 'r:bz2': 'read - bzip2', 'r:xz': 'read - lzma', 'x:': 'create - no compression', 'x:gz': 'create - gzip', 'x:bz2': 'create - bzip2', 'x:xz': 'create - lzma', 'a:': 'append - no compression', 'w:': 'write - no compression', 'w:gz': 'write - gzip', 'w:bz2': 'write - bzip', 'w:xz': 'write - lzma'}

class tar():
	def __init__(self, target_dir=None, compression=None):
		if target_dir is not None:
			self.target_dir = target_dir
		else:
			self.target_dir = os.getcwd()
		self.compression = compression
		self.read_mode, self.write_mode, self.ext = self.set_mode()

	def set_mode(self):
		if self.compression is None:
			write_mode = "w:"
			read_mode = "r:"
			ext = "tar"
		else:
			write_mode = f"w:{self.compression}"
			read_mode = f"r:{self.compression}"
			ext = f"tar.{self.compression}"
		return read_mode, write_mode, ext
			

	def get_files(self, target_dir=None):
		"""Uses subprocess to find all files in a given path and returns a list.
		If none found, returns empty list and logs the error."""

		if target_dir is not None:
			self.target_dir = target_dir
		com = f"find \"{self.target_dir}\" -name \"*.*\""
		try:
			files = subprocess.check_output(com, shell=True).decode().strip().splitlines()
		except Exception as e:
			log(f"Error getting files:{e}", 'error')
			files = []
		return files

	def add_file(self, target, tar_file):
		"""Adds 'target' to 'tar_file'.
		If compression scheme not provided, uses 'tar' extension (no compression)"""

		name = os.path.basename(target)
		fp = tarfile.open(tar_file, self.write_mode)
		#arcname sets a relative path for the file instead of the entire directory structure
		fp.add(target, arcname=name)
		fp.close()

	def detect_compression(self, tar_file):
		"""Helper function to test compression scheme by extension.
		Returns the second half of the 'mode' string.
		If no compression ('tar') extension, returns ':' (no compression)"""

		ext = os.path.splitext(os.path.basename(tar_file))[1].split('.')[1]
		if ext == 'gz':
			mode = ":gz"
		elif ext == 'bz2':
			mode = ":bz2"
		elif ext == 'xz':
			mode = ":xz"
		elif ext == 'tar':
			mode = ":"
		self.compression = mode
		self.set_mode()
		log(f"tar.detect_compression():Changed read/write mode! Read:{self.read_mode}, Write:{self.write_mode}", 'info')
		return mode

	def extract(self, tar_file, target_dir=None):
		"""Extracts and archive to either the current working directory or provided target_dir.
		Detects compression method and sets mode with above 'detect_compression' method.
		Switches current working directory to target for extraction, then returns to original."""

		cwd = os.getcwd()
		if target_dir is not None:
			os.chdir(target_dir)
		self.detect_compression(tar_file)
		fp = tarfile.open(tar_file, self.read_mode)
		fp.extractall()
		fp.close
		os.chdir(cwd)

	def get_common_path(self, files):
		"""Helper function for determining common directory paths (nested dirnames).
		Used to help determine a multi file/directory tree 'arcname' for relative pathing."""

		test1 = files[0]
		testpath = files[1]
		match = False
		while not match:
			test1 = os.path.dirname(test1)
			if test1 in testpath:
				match = True
			else:
				pass
		return test1

	def add_directory(self, target_dir=None, tar_file=None):
		"""Adds the contents (all files/folders) to an archive ('target_dir').
		If compression scheme is None, uses 'tar' extension (no compression)."""

		if target_dir is not None:
			self.target_dir = target_dir
			log(f"tar.add_directory():Target directory changed! ({self.target_directory})", 'info')
		files = self.get_files(self.target_dir)
		cwd = os.getcwd()
		dest_path = self.get_common_path(files)
		path = os.path.dirname(self.target_dir)
		if tar_file is None:
			archive_name = os.path.basename(self.target_dir)
			tar_file = os.path.join(dest_path, f"{archive_name}.{self.ext}")
		fp = tarfile.open(tar_file, self.write_mode)
		for filepath in files:
			fname = os.path.basename(filepath)
			arcname = os.path.join(path, filepath.split(path)[1])
			print("arcname:", arcname)
			fp.add(filepath, arcname=arcname)
			log(f"tar.add_directory():Added to archive '{tar_file}': '{filepath}'", 'info')
		fp.close()
		os.chdir(cwd)
		log(f"Tar archive created! Location:{tar_file}", 'info')
		return tar_file

	def compress(self, target, tar_file=None):
		if not os.path.exists(target):
			txt = f"Error - target doesn't exist! ({target})"
			log(txt, 'error')
			raise Exception(txt)
		if tarfile is None:
			archive_name = os.path.basename(target)
			tar_file = os.path.join(os.getcwd(), f"{archive_name}.{self.ext}")
		if os.path.isfile(target):
			self.add_file(target=target, tar_file=tar_file)
			log(f"Added {target} to {tar_file}!", 'info')
		elif os.path.isdir(target):
			log(f"Adding contents of {target} to {tar_file}...", 'info')
			self.add_directory(target_dir=target, tar_file=tar_file)

			
			
		

