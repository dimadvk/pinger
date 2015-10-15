#!/usr/bin/env python
# -*- coding: utf-8 -*-

#####
#
# Add this script to crontab, set to execute every minute.
#
#####

import time # need for calculate current time
import os # need for start ping processes
import sqlite3
import re

### --- ###
# Name of database for storing data
db_name='db_pinger.sqlite3'
path_to_script = os.path.dirname(__file__)
db = os.path.join(path_to_script, db_name)

# Path to ping utility
ping = '/bin/ping' 

# Monitoring results older then "days_results_obselete" will be removed from base
day_results_obselete = '30'
### --- ###

# if there is no database at path 'db' than create one
if not os.path.isfile(db):
    with sqlite3.connect(db) as conn:
        conn.executescript('''
                CREATE TABLE group_list
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     group_name TEXT,
                     group_comment TEXT);
                CREATE TABLE ip_list
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     ip TEXT,
                     hostname TEXT,
                     group_id INTEGER,
                     FOREIGN KEY (group_id) REFERENCES group_list(id));
                CREATE TABLE ping_results
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     date_time TEXT,
                     ip TEXT,
                     sent INTEGER,
                     received INTEGER)
                ''')

##################

def executeSQL(statement, args=''):
    """
    execute SQL-statement, return result.
    Next type of oraguments is required: 
        'statement' - sql-statement as a string, 'args' - tuple.
    """
    with sqlite3.connect(db) as connection:
        curs = connection.cursor()
        curs.execute(statement, args)
    return curs.fetchall()


def get_ip_list():
    """
    Get from database and return list of ip addresses. Dublicates are filtered
    """
    ip_addr_list = executeSQL('SELECT ip FROM ip_list GROUP BY ip')
    # make [ ('ip1',), ('ip2',), ... ] >> to >> ['ip1', 'ip2', ... ]
    ip_addr_list = [ip[0] for ip in ip_addr_list]
    return ip_addr_list


def pinger(ip_list):
    """
    Starts ping for each IP for one minute and puts the results into database
    """
    ping_processes = {}
    ping_results = {}
    # current date and time "YYYY-mm-dd HH:MM"
    current_time = time.strftime("%Y-%m-%d %H:%M") 

    # start ping for each IP
    for ip in ip_list:
        ping_processes[ip] = os.popen('{0} {1} -c60 -W1 -q'.format(ping, ip))

    # Retrive results of ping for each ip
    for ip in ip_list:
            ping_results[ip] = ping_processes[ip].readlines()
    
    ## write results to database
    for ip in ping_results:
        statistic = []
        # find a row that contains "packet transmitted "+"packet received" and get the numbers
        for row in ping_results[ip]:
            if re.match('^.+packets transmitted.+packets received.+$', row):
                # packets transmitted
                sent = row.split(',')[0].split()[0]
                # packets received
                received = row.split(',')[1].split()[0]
        try:
            sent = int(sent)
            received = int(received)
        except:
            sent, received = 1, 0
        statistic.append(sent)
        statistic.append(received)
        executeSQL('''
            INSERT INTO ping_results(date_time, ip, sent, received) 
                VALUES (?, ?, ?, ?)
                ''', (current_time, ip, statistic[0], statistic[1]))


def delete_old_results(count_of_days):
    """
    Remove monitoring results older than "count_of_days" days
    """
    statement = '''DELETE FROM ping_results 
                        WHERE date(date_time) <= date('now', '-{} days')
                        '''.format(count_of_days)
    executeSQL(statement)

####

# get list of IP for monitoring
ipaddr_list = get_ip_list()
# start monitoring for each ip for 1 minute
pinger(ipaddr_list)
# delete obsolete monitoring results from database
delete_old_results(day_results_obselete)
###################
