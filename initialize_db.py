#!/usr/bin/env python
import os
import sqlite3
from settings import db_name

path_to_script = os.path.dirname(__file__)
db = os.path.join(path_to_script, db_name)
if os.path.isfile(db):
    print """
Error: File "%s" already exists. 
       Change the name for database in settings.py or remove existed file.
""" % db_name
    exit()

with sqlite3.connect(db) as conn:
    conn.execute('''CREATE TABLE group_list 
                    (id integer primary key AUTOINCREMENT, \
                     group_name text, \
                     group_comment text)''')
    conn.execute('''CREATE TABLE ip_list 
                    (id integer primary key AUTOINCREMENT, \
                     ip text, \
                     hostname text, \
                     group_id integer, \
                     foreign key(group_id) references group_list(id))''')
    conn.execute('''CREATE TABLE ping_results 
                    (id integer primary key AUTOINCREMENT, \
                     ip text, \
                     sent text, \
                     received text, \
                     date text, \
                     hour text, \
                     minutes text)''')

