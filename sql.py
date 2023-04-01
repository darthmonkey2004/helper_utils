import sqlite3
from collections import OrderedDict
import os
from helper_utils.log import logger

"""test_table_data = {'table': 'test', 'values': {'key1': 0, 'key2': 'fart', 'key3': 0}}
test_table_create_data = {'table': 'test', 'values': {'key1': {'primary': '1', 'dtype': 'int', 'required': '1', 'value': 0}, 'key2': {'primary': '0', 'dtype': 'str', 'required': '0', 'value': 'fart'}, 'key3': {'primary': '0', 'dtype': 'bool', 'required': '0', 'value': 0}}}"""

logger = logger(verbose=True)
log = logger.log_msg

class sql():
	def __init__(self, database=None):
		if database is None:
			txt = f"sqlite3.create_connection():Error - no database file provided!"
			log(txt, 'error')
			raise Exception(txt)
		self.database = database

	def query(self, query_string):
		conn = sqlite3.connect(self.database)
		cur = conn.cursor()
		try:
			out = []
			cur.execute(query_string)
			rows = cur.fetchall()
			for row in rows:
				out.append(row[0])
			return out
		except Exception as e:
			txt = f"sql.send():Error querying database - {e}, query_string={query_string}!"
			log(txt, 'error')
			raise Exception(txt)

	def send(self, query_string):
		conn = sqlite3.connect(self.database)
		cur = conn.cursor()
		try:
			cur.execute(query_string)
			conn.commit()
		except Exception as e:
			txt = f"sql.send():Error sending to sql - {e}, query_string={query_string}!"
			log(txt, 'error')
			raise Exception(txt)

	def get_columns(self, table):
		conn = sqlite3.connect(self.database)
		cur = conn.cursor()
		query_string = f"PRAGMA table_info=\'{table}\';"
		cur.execute(query_string)
		rows = cur.fetchall()
		ct = len(rows)
		columns = {}
		for row in rows:
			row_data = {}
			row_id, column, data_type, is_required, notaclue, is_primary = row
			row_data['row_id'] = row_id
			row_data['data_type'] = data_type
			row_data['is_required'] = is_required
			row_data['is_primary'] = is_primary
			columns[column] = row_data
		return columns

	def insert(self, data):
		table = data['table']
		columns = sql.get_columns(table)
		d = data['values']
		keys = []
		vals = []
		for key in d.keys():
			dtype = columns[key]['data_type']
			print(dtype)
			if dtype == 'INTEGER' or dtype == 'BOOL':
				val = f"{d[key]}"
			elif dtype == 'TEXT':
				val = f"'{d[key]}'"
			#required = bool(int(columns[key]['is_required']))
			primary = bool(int(columns[key]['is_primary']))
			if not primary:
				keys.append(f"'{key}'")
				vals.append(val)
		keys = ", ".join(keys)
		vals = ", ".join(vals)
		query_string = f"INSERT INTO {table} ({keys}) VALUES({vals});"
		log(f"sql.insert():query_string={query_string}", 'info')
		sql.send(query_string)


	def create_table(self, data):
		table = data['table']
		d = data['values']
		create = f"CREATE TABLE IF NOT EXISTS {table}"
		vals = []
		for item in d.keys():
			primary = False
			required = False
			key = item
			primary = bool(int(d[item]['primary']))
			required = bool(int(d[item]['required']))
			dtype = d[item]['dtype']
			print(f"primary:{primary}, required:{required}, dtype:{dtype}")
			if dtype == 'int':
				dtype = 'INTEGER'
			elif dtype == 'bool':
				dtype = 'BOOL'
			elif dtype == 'str':
				dtype = 'TEXT'
			if primary:
				string = f"{key} {dtype} PRIMARY KEY AUTOINCREMENT"
			else:
				string = f"{key} {dtype}"
			if required:
				string = f"{string} NOT NULL"
			vals.append(string)
		j = ", "
		vals = j.join(vals)
		query = f"{create} ({vals});"
		log(f"sql.create_table():query:'{query}'", 'info')
		sql.send(query)
