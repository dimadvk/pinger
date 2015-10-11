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
        # packets transmitted
        statistic.append(ping_results[ip][3].split(',')[0].split()[0])
        # packets received
        statistic.append(ping_results[ip][3].split(',')[1].split()[0])
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
