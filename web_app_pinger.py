#!/usr/bin/env python
# coding:utf-8

# shpargalka
# create table group_list(id integer primary key AUTOINCREMENT, group_name text, group_comment text);
# create table ip_list(id integer primary key AUTOINCREMENT, ip text, hostname text, group_name text);

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
            row.append('warning_packetloss_level1')
        elif packetloss_count >= 6:
            row.append('warning_packetloss_level2')
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
    date_list.sort(key=lambda x: datetime.datetime.strptime(x, '%d.%m.%Y'))
    return date_list
 
def get_group_and_comment_list(group_id=''):
    '''get group list from base as [(id_1, group1, comment1), (id_2, group2, comment2), ...]'''
    group_list = []
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    if group_id:
        group_list = conn.execute('select id, group_name, group_comment from group_list where id=?', (group_id, ))
    else:
        group_list = conn.execute('select id, group_name, group_comment from group_list')
    group_list = group_list.fetchall()
    return group_list

def get_group_ip_list(group_name):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    group_ip_list = conn.execute('select ip, hostname from ip_list where group_name=?', (group_name, ))
    group_ip_list = group_ip_list.fetchall()
    conn.close()
    return group_ip_list

def add_ip_for_monitoring(ip_addr, hostname, group_name):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    conn.execute('insert into ip_list (ip, hostname, group_name) values (?, ?, ?)', (ip_addr, hostname, group_name))
    conn.commit()
    conn.close()

def add_group(group_name, group_comment):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    conn.execute('insert into group_list (group_name, group_comment) values (?, ?)', (group_name, group_comment))
    conn.commit()
    conn.close()

def delete_group_from_monitoring(group_id):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    group_name = conn.execute('select group_name from group_list where id=?', (group_id, ))
    group_name = group_name.fetchall()
    group_name = group_name[0][0]
    conn.execute('delete from group_list where id=?', (group_id, ))
    conn.execute('delete from ip_list where group_name=?', (group_name, ))
    conn.commit()
    conn.close()
    
def delete_ip_from_monitoring(ip_addr, group_name):
    conn = sqlite3.connect(path_to_db+'pinger_db.sqlite3')
    conn.execute('delete from ip_list where ip=?, group_name=?', (ip_addr, group_name))
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
    return static_file(filename, root='./static/css/')
@route('/img/<filename>')
def img(filename):
    return static_file(filename, root='./static/img/')

@route('/')
def start_page(error_message=''):
    monitoring_list = []
    group_list = get_group_and_comment_list() # [(group_name, comment), ...]
    for group in group_list:
        group_name = group[1]
        group_ip_list = get_group_ip_list(group_name) # [(ip, hostname), ...]
        monitoring_list.append([group, group_ip_list]) # [[(group_id, group_name, comment), [(ip, hostname), ...]], ...]
    return template('start.html', 
                    group_list = group_list,
                    monitoring_list = monitoring_list,
                    error_message=error_message)

@route('/', method='POST')
def add_ip():
    error_message = ''
    ip_addr = request.forms.get('ip')
    ip_addr = re.sub('[ ]', '', ip_addr) # just clear any ' ' from string
    hostname = request.forms.get('hostname').decode('utf-8') # .decode('utf-8') - it needs for sqlite3 accepting cyrillic symbols
    selected_group_name = request.forms.get('group_name')
    new_group_name = request.forms.get('new_group_name')
    new_group_comment = request.forms.get('group_comment')
    if selected_group_name: # if user want to add ip with one of existing group
        selected_group_name = selected_group_name.decode('utf-8')
        group_ip_list = get_group_ip_list(selected_group_name) # [(ip_1, hostname_1), (ip_2, hostname_2), ...]
        group_ip_list = [x[0] for x in group_ip_list] # [ip_1, ip_2, ...]
        if not check_format_ip(ip_addr):
            error_message = 'wrong format of IP'
        elif ip_addr in group_ip_list:
            error_message = 'IP "'+ ip_addr +'" already exists in that group'
        else:
            add_ip_for_monitoring(ip_addr, hostname, selected_group_name)
    elif new_group_name: # if user enter a new group name
        new_group_name = new_group_name.decode('utf-8')
        group_list = get_group_and_comment_list() # it gains [(id_1, group1, comment1), (id_2, group2, comment2)]
        group_list = [x[1] for x in group_list] # it makes group_list == [group1, group2]
        if new_group_name in group_list:
            error_message = 'the group with the name "'+ new_group_name + '" already exists'
        elif not check_format_ip(ip_addr):
            error_message = 'wrong format of IP'
        else:
            if new_group_comment:
                new_group_comment = new_group_comment.decode('utf-8')
            else:
                new_group_comment = 'not commented'
            add_group(new_group_name, new_group_comment)
            add_ip_for_monitoring(ip_addr, hostname, new_group_name)
    else:
        error_message = 'create a new group'
    return start_page(error_message)

@route('/<group_id:re:\d*>')
@route('/<group_id:re:\d*>/<ip_address:re:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}>')
@route('/<group_id:re:\d*>/<ip_address:re:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}>/<date:re:(3[01]|2[0-9]|[01][0-9])\.(1[012]|0[1-9])\.([12][0-9][0-9][0-9])>')
def show_statistic(group_id, ip_address='', date=''):
    group_info = []
    group_id_name_comment = get_group_and_comment_list(group_id)
    if not group_id_name_comment:
        error_message = 'there is no group with id ' + group_id
        return start_page(error_message)
    else:
        group_info.append(group_id_name_comment[0])
    group_name = group_id_name_comment[0][1]
    group_ip_list = get_group_ip_list(group_name)
    group_info.append(group_ip_list)

    if ip_address:
        if not check_format_ip(ip_address):
            return redirect('/'+group_id)
        
    if date and check_format_date(date):
        monitoring_date = date
    else:
        monitoring_date = time.strftime("%d.%m.%Y", time.localtime())
    date_list = get_date_list_when_ip_monitored(ip_address)
    if monitoring_date in date_list:
        db = path_to_db + monitoring_date + '-results.sqlite3'
        ip_statistic = get_statistic_ip(ip_address, db)
    else:
        ip_statistic = []

    return template('ip_statistic.html',
                    group_info=group_info, # group_info = [(group_id, group_name, group_comment), [(ip, hostname), ...]]
                    ip_statistic=ip_statistic, 
                    monitoring_date=monitoring_date, 
                    ip_address=ip_address,
                    date_list=date_list)

@route('/<group_id:re:\d*>/delete')
def delete_group(group_id):
    group_id = int(group_id)
    group_list = get_group_and_comment_list()
    group_id_list = [x[0] for x in group_list ]
    if group_id not in group_id_list:
        error_message = "can't find group with id '"+ group_id +"'"
        return start_page(error_message)
    delete_group_from_monitoring(group_id)
    return redirect('/')


@error(404)
def error404(error):
    return '<h1>Page not found. Error 404.</h1>'

run(host='162.243.89.35', port=8888, debug=True)

###################
###################
