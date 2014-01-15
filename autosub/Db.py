# Autosub Db.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The Autosub DB module
# 

import os
import sqlite3
import logging
import autosub
import autosub.version as version

# Settings
log = logging.getLogger('thelogger')

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class idCache():
    def __init__(self):
        self.query_getId = 'select imdb_id from id_cache where show_name = ?'
        self.query_setId = 'insert into id_cache values (?,?)'
        self.query_flush = 'delete from id_cache'
        
    def getId(self, show_name):
        show_name = show_name
        
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_getId, [show_name.upper()])
        imdb_id = None
        
        for row in cursor:
            imdb_id = row[0]
        
        connection.close()
        if imdb_id:
            return imdb_id
    
    def setId(self, imdb_id, show_name):
        show_name = show_name
        
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_setId,[imdb_id, show_name.upper()])
        connection.commit()
        connection.close()
    
    def flushCache(self):
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_flush)
        connection.commit()
        connection.close()
            
class a7idCache():
    def __init__(self):
        self.query_getId = 'select a7_id from a7id_cache where imdb_id = ?'
        self.query_setId = 'insert into a7id_cache values (?,?)'
        self.query_flush = 'delete from a7id_cache'
        
    def getId(self, imdb_id):
        imdb_id = imdb_id
        
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_getId, [imdb_id])
        a7_id = None
        
        for row in cursor:
            a7_id = row[0]
        
        connection.close()
        if a7_id:
            return a7_id
    
    def setId(self, a7_id, imdb_id):
        imdb_id = imdb_id
        
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_setId,[a7_id, imdb_id])
        connection.commit()
        connection.close()
    
    def flushCache(self):
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_flush)
        connection.commit()
        connection.close()
            
class lastDown():
    def __init__(self):
        self.query_get = 'select * from last_downloads'
        self.query_set = 'insert into last_downloads values (NULL,?,?,?,?,?,?,?,?,?,?)'
        self.query_flush = 'delete from last_downloads'
        
    def getlastDown(self):
        connection=sqlite3.connect(autosub.DBFILE)
        connection.row_factory = dict_factory
        cursor=connection.cursor()
        cursor.execute(self.query_get)
        Llist = cursor.fetchall()
        connection.close()
        return Llist

    def setlastDown (self, **data):
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        Ldict = data['dict']
        
        if not 'source' in Ldict.keys():
            Ldict['source'] = None
        
        cursor.execute(self.query_set,[ 
                       Ldict['title'],
                       Ldict['season'],
                       Ldict['episode'],
                       Ldict['quality'],
                       Ldict['source'],
                       Ldict['downlang'],
                       Ldict['codec'],
                       Ldict['timestamp'],
                       Ldict['releasegrp'],
                       Ldict['subtitle']])
        connection.commit()
        connection.close()
    
    def flushLastdown(self):
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(self.query_flush)
        connection.commit()
        connection.close()

def createDatabase():
    #create the database
    try: 
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        
        cursor.execute("CREATE TABLE id_cache (imdb_id TEXT, show_name TEXT);")
        cursor.execute("CREATE TABLE a7id_cache (a7_id TEXT, imdb_id TEXT);")
        cursor.execute("CREATE TABLE last_downloads (id INTEGER PRIMARY KEY, show_name TEXT, season TEXT, episode TEXT, quality TEXT, source TEXT, language TEXT, codec TEXT, timestamp DATETIME, releasegrp TEXT, subtitle TEXT);")
        cursor.execute("CREATE TABLE info (database_version NUMERIC);")
        connection.commit()
        cursor.execute("INSERT INTO info VALUES (%d)" % version.dbversion)
        connection.commit()
        connection.close()
        
        print "createDatabase: Succesfully created the sqlite database"
        autosub.DBVERSION = version.dbversion
    except:
        "initDatabase: Could not create database, please check if AutoSub has write access to write the following file %s" %autosub.DBFILE
    
    return True

def upgradeDb(from_version, to_version):
    print "upgradeDb: Upgrading database  from version %d to version %d" %(from_version, to_version)
    upgrades = to_version - from_version
    if upgrades != 1:
        print "upgradeDb: %s upgrades are required. Starting subupgrades" % upgrades
        for x in range (0, upgrades):
            upgradeDb((from_version + x, from_version + x + 1))
    else:
        if from_version == 1 and to_version == 2:
            #Add codec and timestamp
            #New table, info with dbversion
            connection=sqlite3.connect(autosub.DBFILE)
            cursor=connection.cursor()
            cursor.execute("ALTER TABLE last_downloads ADD COLUMN '%s' 'TEXT'" % 'codec')
            cursor.execute("ALTER TABLE last_downloads ADD COLUMN '%s' 'TEXT'" % 'timestamp')
            cursor.execute("CREATE TABLE info (database_version NUMERIC);")
            cursor.execute("INSERT INTO info VALUES (%d)" % 2)
            connection.commit()
            connection.close()
        if from_version == 2 and to_version == 3:
            #Add Releasegrp
            connection=sqlite3.connect(autosub.DBFILE)
            cursor=connection.cursor()
            cursor.execute("ALTER TABLE last_downloads ADD COLUMN '%s' 'TEXT'" % 'releasegrp')
            cursor.execute("ALTER TABLE last_downloads ADD COLUMN '%s' 'TEXT'" % 'subtitle')
            cursor.execute("UPDATE info SET database_version = %d WHERE database_version = %d" % (3,2))
            connection.commit()
            connection.close()
        if from_version == 3 and to_version == 4:
            #Change IMDB_ID from INTEGER to TEXT
            connection=sqlite3.connect(autosub.DBFILE)
            cursor=connection.cursor()
            cursor.execute("CREATE TABLE temp_table as select * from id_cache;")
            cursor.execute("DROP TABLE id_cache;")
            cursor.execute("CREATE TABLE id_cache (imdb_id TEXT, show_name TEXT);")
            cursor.execute("INSERT INTO id_cache select * from temp_table;")
            cursor.execute("DROP TABLE temp_table;")
            cursor.execute("UPDATE info SET database_version = %d WHERE database_version = %d" % (4,3))
            connection.commit()
            connection.close()
        if from_version == 4 and to_version == 5:
            connection=sqlite3.connect(autosub.DBFILE)
            cursor=connection.cursor()
            cursor.execute("CREATE TABLE a7id_cache (a7_id TEXT, imdb_id TEXT);")
            cursor.execute("UPDATE info SET database_version = %d WHERE database_version = %d" % (5,4))
            connection.commit()
            connection.close()
        if from_version == 5 and to_version == 6:
            #Clear id cache once, so we don't get invalid reports about non working IMDB/A7 ID's
            connection=sqlite3.connect(autosub.DBFILE)
            cursor=connection.cursor()
            cursor.execute("delete from id_cache;")
            cursor.execute("delete from a7id_cache;")
            cursor.execute("UPDATE info SET database_version = %d WHERE database_version = %d" % (6,5))
            connection.commit()
            connection.close()
            

def getDbVersion():
    try:
        query_getVersion = 'SELECT database_version FROM info'
        connection=sqlite3.connect(autosub.DBFILE)
        cursor=connection.cursor()
        cursor.execute(query_getVersion)
        
        for row in cursor:
            dbversion = row[0]
        connection.close()
        
        return int(dbversion)
    except:
        return 1

def initDatabase():
    #check if file is already there
    dbFile = os.path.join(autosub.PATH, autosub.DBFILE)
    if not os.path.exists(dbFile):
        createDatabase()
    
    autosub.DBVERSION = getDbVersion()
    
    if autosub.DBVERSION < version.dbversion:
        upgradeDb(autosub.DBVERSION, version.dbversion)
    elif autosub.DBVERSION > version.dbversion:
        print "initDatabase: Database version higher then this version of AutoSub supports. Update!!!"
        os._exit(1)
