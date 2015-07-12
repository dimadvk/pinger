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
from settings import ping, db_name

path_to_script = os.path.dirname(__file__)
db = os.path.join(path_to_script, db_name)


##################

def get_ip_list():
    conn = sqlite3.connect(db)
    get_ip = conn.execute('select ip from ip_list')
    get_ip = get_ip.fetchall()
    conn.close()
    ipaddr_list = []
    for ip in get_ip:
        ipaddr_list.append(ip[0])
    ipaddr_list = list(set(ipaddr_list)) # remove dublicate IP addresses
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
    conn = sqlite3.connect(db)
    for ip in ping_results:
        statistic = []
        statistic.append(ping_results[ip][3].split(',')[0].split()[0]) # packets transmitted
        statistic.append(ping_results[ip][3].split(',')[1].split()[0]) # packets received
        conn.execute('insert into ping_results(ip, sent, received, date, hour, minutes) values (?, ?, ?, ?, ?, ?)', (ip, statistic[0], statistic[1], cur_time[0], cur_time[1], cur_time[2] ))
    conn.commit()
    conn.close()


####

ipaddr_list = get_ip_list()
pinger(ipaddr_list)

####
