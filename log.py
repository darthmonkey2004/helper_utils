import traceback, sys
import logging
import datetime
import os


"""configurable logger class, for use where I keep needing one... (REUSABLE)"""

class logger():
	"""Main logger class."""
	def __init__(self, logfile=None, default_log_level='info', verbose=False):
		"""Initializes logger class.
		
		Sets log filepath and creating directory if needed.
		If the logfile is provided, sets as class attribute, otherwise is set as None.
		Default logfile is in user's home directory as 'log.txt'.
		Set current default log_level with self.set_default_log_level(), or by log_level class attribute.
		Temporary logging levels can be set in log_msg(log_level=1/2/3...)"""

		if logfile is None:
			self.logfile = os.path.join(os.path.expanduser("~"), 'log.txt')
		else:
			self.logfile = logfile
		self.log_level = self.set_default_log_level(default_log_level)
		#logging.basicConfig(filename=self.logfile, level=self.log_level)
		self.verbose = verbose

	def set_verbose(self, verbose):
		if type(verbose) != bool:
			raise TypeError(f"Error: verbose flag must be True/False!")
		self.verbose = verbose

	def _init_logfile(self):
		"""Helper function to initialize and create logging file and directory.
		
		Parses logging directory from filepath.
		Tests to see if directory exists, creates if not."""
		
		logdir = os.path.dirname(self.logfile)
		os.makedirs(logdir, exist_ok=True)
		self.touch(self.logfile)

	def _touch(self, logfile):
		"""Helper function, simulates 'touch' command in terminal. Creates empty file."""

		with open(logfile, 'w+') as f:
			f.close()

	def _test_log_level(self, log_level):
		if isinstance(log_level, str):
			log_level = self.convert_lvl_to_int(log_level)
		if not isinstance(log_level, int):
			return False
		return True

	def set_default_log_level(self, log_level):
		"""Function that for setting valid log_levels.
		Accepts lowercase strings, uppercase strings, and integer arguments for log_level.
		Sets basicConfig to use class attributes logfile and log_level."""

		if self._test_log_level(log_level):
			log_level_int = self.convert_lvl_to_int(log_level)
			logging.basicConfig(filename=self.logfile, level=log_level_int)
			return log_level
		else:
			raise ValueError(f"Invalid log level: {log_level}")

	def convert_lvl_to_int(self, lvl):
		return getattr(logging, lvl.upper(), None)

	def log_msg(self, msg=None, log_level=None):
		"""Main logger function for class.
		Functionality:
			- checks for no message data, raises error if None.
			- Tests log_level, raises error if invalid (non-numeric)
			- Allows override of current default (or provided log level) if 'self.verbose' is True
			- Prints all messages if level is debug or verbose is set."""


		if msg is None:
			raise ValueError(f"logger.log_msg():No message data provided!")
		if log_level is None:
			log_level = self.log_level
		else:
			if not self._test_log_level(log_level):
				raise TypeError(f"Invalid log_level used: {log_level}!")
		lvl = self.convert_lvl_to_int(log_level)
		if self.verbose and lvl != 40:
			# if verbose flag == True, override debug value and print all messages (unless error)
			logging.debug("log.log_msg():Overriding log level (verbose=True)")
			print(f"DEBUG(verbose=True)::{msg}")
		elif not self.verbose:
			if lvl == 10:#debug level
				logging.debug(msg)
				print(f"DEBUG::{msg}")
			elif lvl == 20:
				logging.info(msg)
			elif lvl == 30:
				logging.warning(msg)
		elif lvl == 40:
			t = datetime.datetime.now()
			ts = (str(t.day) + "-" + str(t.month) + "-" + str(t.year) + " " + str(t.hour) + ":" + str(t.minute) + ":" + str(t.second) + ":" + str(t.microsecond))
			try:
				formatted_lines = traceback.format_exc().splitlines()
				j = "\n"
				tb_text = j.join(formatted_lines)
				msg = (f"{ts}::{msg}\n{tb_text}")
				print(f"ERROR:{msg}")
			except Exception as e:
				print("tb_text", tb_text)
				msg = (f"{ts}::{msg}\nUnable to insert traceback info({e})")
			logging.error(msg)
		
