
from .base import *

import errno
import warnings

import MySQLdb

class mysql(driver_base):
	"""Driver for mysql databases

	mysql requires only one parameter: database, which is the name of the
	database to use. 
	"""
	test_args = ('silk_test','silk_test')
	test_kwargs = {'engine':'InnoDB'}
	
	parameters = driver_base.parameters_format
	id_quote = '`'
	
	def __init__(self, database, user='root', password=None, host='localhost', engine='MyISAM', debug=False):
		driver_base.__init__(self, MySQLdb.connect(host=host, user=user, passwd=password or '', db=database), debug)
		self.database = database
		self.host = host
		self.user = user
		self.password = password
		self.engine = engine

	@property
	def engine(self):
		return self.__dict__['engine']
	@engine.setter
	def engine(self, new):
		assert new in {'MyISAM','InnoDB','MERGE','MEMORY','BDB','EXAMPLE','FEDERATED','ARCHIVE','CSV','BLACKHOLE'}, 'Unknown storage engine %r' % new
		if new in {'InnoDB', 'BDB'}:
			self.features.add('transactions')
		else:
			self.features.discard('transactions')
		self.__dict__['engine'] = new

	webdb_types = {
		int:'INT',
		float:'REAL',
		bool:'TINYINT(1)',
		unicode:'VARCHAR(512)',
		bytes:'BLOB',
		datetime.datetime:'DATETIME',
	}

	def handle_exception(self, e):
		if isinstance(e, MySQLdb.OperationalError):
			raise e
			#msg = e.args[0]
			#if 'has no column named' in msg or msg.startswith('no such column: '):
				#raise KeyError("No such column in table: %s" % msg.rsplit(None, 1)[1])

	def unmap_type(self, t):
		name, y, size = t.partition('(')
		if y:
			size = int(size[:-1])
		if name in ('int','tinyint'):
			return int if size > 1 else bool
		elif name in ('text','varchar'):
			return unicode
		elif name == 'timestamp':
			return datetime.datetime
		elif name in ('double','real'):
			return float
		elif name in ('blob',):
			return bytes
	
	def list_tables_sql(self):
		return """SHOW TABLES;"""
		
	def list_columns(self, table):
		for name,v_type,null,key,default,extra in self.execute("""DESCRIBE %s;""" % table):
			ut = self.unmap_type(v_type)
			if not ut:
				raise Exception('Unknown column type %s' % v_type)
			yield (str(name),ut,null!='YES',default)

	def create_table_if_nexists(self, name, columns, primarykeys):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			return self.execute("""CREATE%s TABLE IF NOT EXISTS %s(%s, PRIMARY KEY (%s)) ENGINE=%s;""" % (
				' TEMPORARY' if self.debug else '',
				name,
				', '.join(columns),
				', '.join('%s ASC'%p for p in primarykeys),
				self.engine
			))

	def insert_rowid(self, cursor):
		return self.connection.insert_id()
