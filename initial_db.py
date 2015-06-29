#!/usr/bin/env python
import sqlite3

database='pinger_db.sqlite3'

conn = sqlite3.connect(database)
conn.execute('CREATE TABLE group_list (id integer primary key AUTOINCREMENT, \
                                       group_name text, \
                                       group_comment text)')
conn.execute('CREATE TABLE ip_list (id integer primary key AUTOINCREMENT, \
                                    ip text, \
                                    hostname text, \
                                    group_id integer)')
conn.execute('CREATE TABLE ping_results (id integer primary key AUTOINCREMENT, \
                                         ip text, \
                                         sent text, \
                                         received text, \
                                         date text, \
                                         hour text, \
                                         minutes text)')
conn.commit()
conn.close()


# create table group_list(id integer primary key AUTOINCREMENT, group_name text, group_comment text);
# create table ip_list (id INTEGER PRIMARY KEY autoincrement, ip text, hostname text, group_id integer);

