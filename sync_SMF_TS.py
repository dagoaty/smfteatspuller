#!/usr/bin/env python

import sys
import ts3
import MySQLdb
import sqlite3

mysql = {'dbhost': '',
         'dbuser': '',
         'dbpass': '',
         'dbname': '',
        }

sqlite = {'dbfile': '',
          'serverid': '',
         }

teamspeak = {'dbhost': '',
             'dbuser': '',
             'dbpass': '',
             'dbport': '',
             'groupid': '',
             'serverid': sqlite['serverid'],
            }

def connect_mysql():
    '''Make a connection to the mysql server'''
    try:
        con = MySQLdb.connect(mysql['dbhost'], mysql['dbuser'], mysql['dbpass'], mysql['dbname'])
    except MySQLdb.Error, e:
        print "Error %s: %s" % (e.args[0], e.args[1])
        sys.exit(1)

    return con

def connect_sqlite3():
    '''Make a connection to the ts3 sqlite file'''
    try:
        con = sqlite3.connect(sqlite['dbfile'])
    except sqlite3.Error:
        print "Error opening sqlite db"
        sys.exit(1)

    return con

def connect_ts3():
   '''Make a connection to the ts3 query port'''
    con = ts3.TS3Server(teamspeak['dbhost'], teamspeak['dbport'])
    con.login(teamspeak['dbuser'], teamspeak['dbpass'])
    try:
        con.use(teamspeak['serverid'])
    except:
        print "Error connecting to Teamspeak"
        sys.exit(1)

    return con

def get_mysql_unique_ids():
    '''Returns a list of all UniqueIDs in the DB which have matched TEA rule 1'''
    con = connect_mysql()
    ids = []
    query = '''SELECT smf_tea_ts_users.tsid
               FROM smf_tea_ts_users, smf_tea_api
               WHERE smf_tea_api.ID_MEMBER = smf_tea_ts_users.id
               AND smf_tea_api.matched LIKE "1;%";'''
    cur = con.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    con.close()

    for row in rows:
        ids.append(row[0])
    return ids

def get_ts_unique_ids():
    '''Returns a list of all UniqueIDs in the teamspeak group'''
    con = connect_ts3()
    unique_ids = []
    response = con.send_command('servergroupclientlist', keys={'sgid': teamspeak['groupid']}, opts=('names',))

    for client in response.data:
        if 'client_unique_identifier' in client:
            unique_ids.append(client['client_unique_identifier'])
    con.disconnect()

    return unique_ids

def list_comp(list1, list2):
    '''Returns items in list1 which are not in list2'''
    return [x for x in list1 if x not in list2]

def remove_from_ts(ids):
    '''Removes the list of ids from the teamspeak group.
       This will leave known IDs in the guest group'''
    con = connect_ts3()
    ts_db_ids = []
    for id in ids:
        response = con.send_command('clientdbfind', keys={'pattern': id}, opts=('uid',))
        for client in response.data:
            if 'cldbid' in client:
                ts_db_ids.append(client['cldbid'])

    for id in ts_db_ids:
        response = con.send_command('servergroupdelclient', keys={'sgid': teamspeak['groupid'], 'cldbid': id})
    con.disconnect()

    return len(ts_db_ids)

def add_to_ts(ids):
    '''Adds a list of ids to the sqlite file and then assigns them to the group'''
    sqlite_con = connect_sqlite3()
    sqlite_cur = sqlite_con.cursor()
    ts_con = connect_ts3()
    cldbids = []

    for id in ids:
        sql = 'SELECT client_id FROM clients WHERE client_unique_id = ?'
        sqlite_cur.execute(sql, (id,))
        cldbid = sqlite_cur.fetchone()
        if not cldbid:
            sql = 'INSERT INTO clients (server_id, client_unique_id) VALUES (?, ?)'
            sqlite_cur.execute(sql, (sqlite['serverid'], id,))
            sqlite_con.commit()
        sql = 'SELECT client_id FROM clients WHERE client_unique_id = ?'
        sqlite_cur.execute(sql, (id,))
        cldbid = sqlite_cur.fetchone()
        cldbids.append(cldbid[0])
    sqlite_con.close()

    for cldbid in cldbids:
        ts_con.send_command('servergroupaddclient', keys={'sgid': teamspeak['groupid'], 'cldbid': cldbid})
    ts_con.disconnect()

    return len(cldbids)

tsuniqueids = get_ts_unique_ids() # Get the list of UniqueIDs in the group of interest in Teamspeak
mysqluniqueids = get_mysql_unique_ids() # Get the list of UniqueIDs from SMF's DB

ids_to_remove_from_ts = list_comp(tsuniqueids, mysqluniqueids) # Calculate the IDs to remove from TS
ids_to_add_to_ts = list_comp(mysqluniqueids, tsuniqueids) # Calculate the IDs to add to TS
