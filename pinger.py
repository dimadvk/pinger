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

db_ip_list='pinger_db.sqlite3'
path_to_db='../database/'
ping = '/bin/ping'

def initial_db(dbName):
    conn = sqlite3.connect(dbName)
    conn.execute('create table ping_results(id integer primary key AUTOINCREMENT, \
                                            ip text, \
                                            sent text, \
                                            received text, \
                                            loss text, \
                                            date text, \
                                            hour text, \
                                            minutes text);')
    conn.commit()
    conn.close()


def get_ip_list(database):
    conn = sqlite3.connect(database)
    get_ip = conn.execute('select ip from ip_list')
    get_ip = get_ip.fetchall()
    conn.close()
    ipaddr_list = []
    for ip in get_ip:
        ipaddr_list.append(ip[0])
    return ipaddr_list

def pinger(ip_list):
    '''This func starts ping for each IP with option -c60 and put results into database'''
    ping_processes = {}
    ping_results = {}
    cur_time = (time.strftime("%d.%m.%Y", time.localtime()), time.strftime("%H", time.localtime()), time.strftime("%M", time.localtime())) # current time (date, hour, minute)
    for ip in ip_list:
        ping_processes[ip] = os.popen('{0} {1} -c60 -W1 -q'.format(ping, ip))
    for ip in ip_list:
            ping_results[ip] = ping_processes[ip].readlines()
    ## write results to database >>
    db = path_to_db+cur_time[0]+'-results.sqlite3' # cur_time[0] == dd.mm.yyyy
    if not os.path.exists(db): ## check database exists. If not - create one
        initial_db(db)
    conn = sqlite3.connect(db)
    ping_statistics = {}
    for ip in ping_results:
        statistic = []
        statistic.append(ping_results[ip][3].split(',')[0].split()[0]) # packets transmitted
        statistic.append(ping_results[ip][3].split(',')[1].split()[0]) # packets received
        if ping_results[ip][3].split(',')[2].split()[0].startswith('+') == False: # # packets loss, not '+<num> errors'
            statistic.append(ping_results[ip][3].split(',')[2].split()[0])
        else:
            statistic.append(ping_results[ip][3].split(',')[3].split()[0])
        ping_statistics[ip] = statistic
        conn.execute('insert into ping_results(ip, sent, received, loss, date, hour, minutes) values (?, ?, ?, ?, ?, ?, ?)', (ip, statistic[0], statistic[1], statistic[2], cur_time[0], cur_time[1], cur_time[2] ))
    conn.commit()
    conn.close()


####

ipaddr_list = get_ip_list(path_to_db + db_ip_list)
pinger(ipaddr_list)
