#!/usr/bin/env python
# coding:utf-8


##### To Do List #####
"""
- add checkin is database 'pinger_db.sqlite3' exists when server starts.
    If no 'pinger_db.sqlite3' exists initialize new one.
    How will it work with Apache?
- add checking is anyone database with results exists. 
    If not return page with message 'Can't find any results. Add pinger.py to crontab. Wait 1 minute for first results' or something like this.
- move all functions (except functions with @route) from here to one specialized module-file
- add_ip() -- if IP not added due to a wrong format return page with error message
- if user del some IP or group return start page with a message 'group/IP deleted. Undo?'. Link 'Undo' must set group/IP back to list.

"""
######################


from bottle import run, route, error, static_file, template, request, redirect
import time, datetime
import sqlite3
import os
import re

abs_path_to_script = os.path.dirname(__file__)
path_to_db = os.path.join(abs_path_to_script, '../database/')


#########
def get_statistic_day(ip, db):
    '''get a summary day monitoring statistic for ip (ip, sent, received, loss)'''
    conn = sqlite3.connect(db)
    get_results_ip = conn.execute('select * from ping_results where ip=?', (ip, ))
    get_results_ip = get_results_ip.fetchall()
    conn.close()
    transmitted, received, loss = 0.0, 0.0, 0.0
    for record in get_results_ip:
        transmitted = transmitted + int(record[2])
        received = received + int(record[3])
    if transmitted > 0:
        loss = (transmitted - received)*100/transmitted
    day_result = (ip, int(transmitted), int(received), int(loss))
    return day_result

def get_statistic_ip(ip, db):
    '''get a day monitoring statistic for ip [[hour, minutes, sent, received, loss, color], ... ]'''
    conn = sqlite3.connect(db)
    get_results_ip = conn.execute('select hour, minutes, sent, received, loss from ping_results where ip=?', (ip, ))
    get_results_ip = get_results_ip.fetchall()
    conn.close()
    statistic_ip = []
    for row in get_results_ip:
        row = list(row)
        packetloss_count = int(row[2]) - int(row[3])
        if packetloss_count ==0:
            row.append('')
        elif 0 < packetloss_count < 6:
            row.append('#FFACC3')
        elif packetloss_count >= 6:
            row.append('#FF6A66')
        statistic_ip.append(row)
    return statistic_ip

def get_existing_bases():
    '''get a list of existing bases with results ['dd.mm.yyyy', ]'''
    list_existing_bases = []
    list_dir = os.listdir(path_to_db)
    for file_name in list_dir:
        if re.match('^\d\d\.\d\d\.\d\d\d\d-results.sqlite3$', file_name):
            base = re.sub('-results.sqlite3$', '', file_name)
            list_existing_bases.append(base)
    return list_existing_bases

def get_date_list_when_ip_monitored(ip):
    list_existing_bases = []
    date_list = []
    list_dir = os.listdir(path_to_db)
    for file_name in list_dir:
        if re.match('^\d\d\.\d\d\.\d\d\d\d-results.sqlite3$', file_name):
            list_existing_bases.append(file_name)
    for base_name in list_existing_bases:
        conn = sqlite3.connect(path_to_db + base_name)
        get_ip = conn.execute('select * from ping_results where ip=? limit 1', (ip, ))
        get_ip = get_ip.fetchall();
        conn.close()
        if get_ip:
            date = re.sub('-results.sqlite3$', '', base_name)
            date_list.append(date)
    return date_list
 

def get_ip_comment_list():
    '''get list of ip adresses from monitoring base'''
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    ip_comment_list = conn.execute('select ip, comment from ip_list')
    ip_comment_list = ip_comment_list.fetchall()
    conn.close()
    return ip_comment_list

def get_ip_list():
    '''get list of ip adresses from monitoring base'''
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    ip_list = conn.execute('select ip from ip_list')
    ip_list = ip_list.fetchall()
    ip_list = [ip[0] for ip in ip_list]
    conn.close()
    return ip_list

def add_ip_for_monitoring(ip_addr, comment):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    conn.execute('insert into ip_list (ip, comment) values (?, ?)', (ip_addr, comment))
    conn.commit()
    conn.close()
    
def delete_ip_from_monitoring(ip_addr):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    conn.execute('delete from ip_list where ip=?', (ip_addr, ))
    conn.commit()
    conn.close()
    

def check_format_ip(ip):
    if re.match('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return 1
    else:
        return 0

def check_format_date(date):
    if re.match('^(3[01]|2[0-9]|[01][0-9])\.(1[012]|0[1-9])\.([12][0-9][0-9][0-9])$', date):
        return 1
    else:
        return 0
   

#########


@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='./static/')

@route('/')
def start_page():
    ip_list = get_ip_list()
    ip_comment_list = get_ip_comment_list()
    cur_date = time.strftime("%d.%m.%Y", time.localtime())
    db_results = path_to_db+cur_date+'-results.sqlite3'
    day_statistic = []
    for ip_addr in ip_list:
        day_result_ip = get_statistic_day(ip_addr, db_results)
        day_statistic.append(day_result_ip)
    #
    return template('start.html', 
                    ip_comment_list=ip_comment_list, 
                    day_statistic=day_statistic, 
                    current_date=cur_date)

@route('/', method='POST')
def add_ip():
    ip_addr = request.forms.get('ip')
    ip_addr = re.sub('[ ]', '', ip_addr)
    comment = request.forms.get('comment')
    ip_list = get_ip_list()
    if (ip_addr not in ip_list) and check_format_ip(ip_addr):
       add_ip_for_monitoring(ip_addr, comment)
    return start_page()

@route('/<ip_address>')
@route('/<ip_address>/<date:re:(3[01]|2[0-9]|[01][0-9])\.(1[012]|0[1-9])\.([12][0-9][0-9][0-9])>')
def get_statistic_one_ip(ip_address, date=''):
    if not check_format_ip(ip_address):
        return redirect('/')
    if date and check_format_date(date):
        monitoring_date = date
    else:
        monitoring_date = time.strftime("%d.%m.%Y", time.localtime())
    ip_comment_list = get_ip_comment_list()
    date_list = get_date_list_when_ip_monitored(ip_address)
    date_list.sort(key=lambda x: datetime.datetime.strptime(x, '%d.%m.%Y'))
    if monitoring_date in date_list:
        db = path_to_db + monitoring_date + '-results.sqlite3'
        ip_statistic = get_statistic_ip(ip_address, db)
    else:
        ip_statistic = []
    return template('ip_statistic.html',
                    ip_address=ip_address,
                    ip_statistic=ip_statistic, 
                    monitoring_date=monitoring_date, 
                    ip_comment_list=ip_comment_list,
                    date_list=date_list)

@route('/<ip_address>/delete')
def delete_ip(ip_address):
    ip_list = get_ip_list()
    if ip_address not in ip_list:
        return redirect('/')
    delete_ip_from_monitoring(ip_address)
    return redirect('/')


@error(404)
def error404(error):
    return '<h1>Page not found. Error 404.</h1>'

run(host='162.243.89.35', port=8888, debug=True)

###################
###################
