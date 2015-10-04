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
    conn.executescript('''
            CREATE TABLE group_list
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 group_name text,
                 group_comment text);
            CREATE TABLE ip_list
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ip text,
                 hostname text,
                 group_id integer,
                 FOREIGN KEY (group_id) REFERENCES group_list(id));
            CREATE TABLE ping_results
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 date_time text,
                 ip text,
                 sent text,
                 received text)
            ''')

