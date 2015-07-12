#!/usr/bin/env python
# coding:utf-8

# shpargalka
# create table group_list(id integer primary key AUTOINCREMENT, group_name text, group_comment text);
# create table ip_list (id INTEGER PRIMARY KEY autoincrement, ip text, hostname text, group_id integer);
"""
select hour, ip, sum(sent), sum(received), (sum(sent)-sum(received))*100/sum(sent) as loss from ping_results  group by ip, hour order by ip;
"""


##### To Do List #####
"""
- add checkin is database 'pinger_db.sqlite3' exists when server starts.
    If no 'pinger_db.sqlite3' exists initialize new one.
- add checking is anyone database with results exists. 
    If not return page with message 'Can't find any results. Add pinger.py to crontab. Wait 1 minute for first results' or something like this.
- move all functions (except functions with @route) from here to one specialized module-file
- убрать кучу файлов с результатами, все писать только в один файл pinger_db.sqlite3
- remome monitoring results older than 2 month


"""
######################


from bottle import run, route, error, static_file, template, request, redirect
import time, datetime
import sqlite3
import os
import re
from settings import db_name

path_to_script = os.path.dirname(__file__)
db = os.path.join(path_to_script, db_name)

#########

def get_statistic_ip_day(ip, date):
    '''get a day monitoring statistic for ip [[hour, sent, received, loss_percent, hour_num, warning_level], ... ]'''
    conn = sqlite3.connect(db)
    get_results_ip = conn.execute('select hour, \
                                          sum(sent),\
                                          sum(received),\
                                          (sum(sent)-sum(received))*100/sum(sent) as loss_percent \
                                            from ping_results where ip=? and date= ? group by hour', (ip, date))
    get_results_ip = get_results_ip.fetchall()
    conn.close()
    statistic_ip = []
    for row in get_results_ip:
        row = list(row)
        hour_num = row[0]
        row.append(hour_num)
        row[0] = row[0]+':00-'+str(int(row[0])+1)+':00' # it makes hour: '01' >> '1:00-2:00'
        packetloss = int(row[3])
        if packetloss ==0:
            row.append('')
        elif 0 < packetloss < 6:
            row.append('warning_packetloss_level1')
        elif packetloss >= 6:
            row.append('warning_packetloss_level2')
        statistic_ip.append(row)
    return statistic_ip

def get_statistic_ip_hour(ip, date, hour):
    '''get a monitoring statistic for ip for specified hour [[hour, minute, sent, received, loss, warning_level], ... ]'''
    conn = sqlite3.connect(db)
    get_results_ip = conn.execute('select hour,\
                                          minutes,\
                                          sent,\
                                          received,\
                                          (sent - received)*100/sent as loss_percent \
                                            from ping_results where ip=? and date=? and hour=?', (ip, date, hour))
    get_results_ip = get_results_ip.fetchall()
    conn.close()
    statistic_ip_hour = []
    for row in get_results_ip:
        row = list(row)
        packetloss = int(row[4])
        if packetloss ==0:
            row.append('')
        elif 0 < packetloss < 6:
            row.append('warning_packetloss_level1')
        elif packetloss >= 6:
            row.append('warning_packetloss_level2')
        statistic_ip_hour.append(row)
    return statistic_ip_hour


def get_date_list_when_ip_monitored(ip_address):
    conn = sqlite3.connect(db)
    date_list = conn.execute('select date from ping_results where ip=? group by date', (ip_address, ))
    date_list = date_list.fetchall() # it returns [ (date1), (date2), ... ]
    conn.close()
    date_list = [date[0] for date in date_list] # it returns [ date1, date2, ... ]
    date_list.sort(key=lambda x: datetime.datetime.strptime(x, '%d.%m.%Y'))
    return date_list
 
def get_group_and_comment_list(group_id=''):
    '''get group list from base as [(id_1, group1, comment1), (id_2, group2, comment2), ...]'''
    group_list = []
    conn = sqlite3.connect(db)
    if group_id:
        group_list = conn.execute('select id,\
                                          group_name,\
                                          group_comment\
                                            from group_list where id=?', (group_id, ))
    else:
        group_list = conn.execute('select id,\
                                          group_name,\
                                          group_comment\
                                            from group_list order by id DESC')
    group_list = group_list.fetchall()
    return group_list

def update_group_comment(group_id, new_group_comment):
    conn = sqlite3.connect(db)
    conn.execute('update group_list set group_comment=? where id=?', (new_group_comment, group_id))
    conn.commit()
    conn.close()

def get_group_ip_list(group_id):
    """it returns list [(ip, hostname), (ip2, hostname2) ... ]"""
    conn = sqlite3.connect(db)
    group_ip_list = conn.execute('select ip, hostname from ip_list where group_id=?', (group_id, ))
    group_ip_list = group_ip_list.fetchall()
    conn.close()
    return group_ip_list

def add_ip_for_monitoring(ip_address, hostname, group_id):
    conn = sqlite3.connect(db)
    conn.execute('insert into ip_list (ip, hostname, group_id) values (?, ?, ?)', (ip_address, hostname, group_id))
    conn.commit()
    conn.close()

def add_group(group_name, group_comment):
    conn = sqlite3.connect(db)
    curs = conn.execute('insert into group_list (group_name, group_comment) values (?, ?)', (group_name, group_comment))
    new_group_id = curs.lastrowid
    conn.commit()
    conn.close()
    return new_group_id

def delete_group_from_monitoring(group_id):
    if get_group_and_comment_list(group_id=group_id):
        conn = sqlite3.connect(db)
        conn.execute('delete from group_list where id=?', (group_id, ))
        conn.execute('delete from ip_list where group_id=?', (group_id, ))
        conn.commit()
        conn.close()

def delete_ip_from_monitoring(group_id, ip_address):
    group_name_comment = get_group_and_comment_list(group_id=group_id)
    if get_group_and_comment_list(group_id=group_id):
        group_ip_hostname_list = get_group_ip_list(group_id)
        group_ip_list = [x[0] for x in group_ip_hostname_list]
        if ip_address in group_ip_list:
            conn = sqlite3.connect(db)
            conn.execute('delete from ip_list where ip=? and group_id=?', (ip_address, group_id))
            conn.commit()
            conn.close()


    
###

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
def static_css(filename):
    return static_file(filename, root='static/css/')
@route('/img/<filename>')
def static_img(filename):
    return static_file(filename, root='./static/img/')

@route('/')
def start_page(error_message=''):
    if request.query.action:
        if request.query.action == "delete_group" and request.query.group_id:
                group_id = int(request.query.group_id)
                delete_group_from_monitoring(group_id)
                return redirect(request.path)
        elif request.query.action == "delete_ip" and request.query.group_id and request.query.ip_addr:
                group_id = int(request.query.group_id)
                ip_address = request.query.ip_addr
                delete_ip_from_monitoring(group_id, ip_address)
                return redirect(request.path)
        else:
                return redirect(request.path)
    monitoring_list = []
    group_list = get_group_and_comment_list() # [(group_id, group_name, group_comment), ...]
    for group in group_list:
        group_id = group[0]
        group_ip_list = get_group_ip_list(group_id) # [(ip, hostname), ...]
        monitoring_list.append([group, group_ip_list]) # [[(group_id, group_name, group_comment), [(ip, hostname), ...]], ...]
    return template('start.html', 
                    group_list = group_list,
                    monitoring_list = monitoring_list,
                    error_message=error_message,
                    page_title = 'Pinger')

@route('/', method='POST')
def add_ip():
    error_message = ''
    ip_addr = request.forms.get('ip')
    ip_addr = re.sub('[ ]', '', ip_addr) # just clear any ' ' from string
    hostname = request.forms.get('hostname').decode('utf-8') # .decode('utf-8') - it needs for sqlite3 accepting cyrillic symbols
    selected_group_id = request.forms.get('select_group')
    if selected_group_id:
        selected_group_id = int(selected_group_id)
    new_group_name = request.forms.get('new_group_name')
    new_group_comment = request.forms.get('group_comment')
    if selected_group_id: # if user want to add ip with one of existing group
        group_ip_list = get_group_ip_list(selected_group_id) # [(ip_1, hostname_1), (ip_2, hostname_2), ...]
        group_ip_list = [x[0] for x in group_ip_list] # [ip_1, ip_2, ...]
        if not check_format_ip(ip_addr):
            error_message = 'wrong format of IP'
        elif ip_addr in group_ip_list:
            error_message = 'IP "'+ ip_addr +'" already exists in that group'
        else:
            add_ip_for_monitoring(ip_addr, hostname, selected_group_id)
    elif new_group_name: # if user enter a new group name
        new_group_name = new_group_name.decode('utf-8')
        group_list = get_group_and_comment_list() # it gains [(id_1, group1, comment1), (id_2, group2, comment2)]
        group_name_list = [x[1] for x in group_list] # it makes group_list == [group1, group2]
        if new_group_name in group_name_list:
            error_message = 'the group with the name "'+ new_group_name + '" already exists'
        elif not check_format_ip(ip_addr):
            error_message = 'wrong format of IP'
        else:
            if new_group_comment:
                new_group_comment = new_group_comment.decode('utf-8')
            else:
                new_group_comment = 'not commented'
            new_group_id = add_group(new_group_name, new_group_comment)
            # get group_id of new group as new_group_id

            add_ip_for_monitoring(ip_addr, hostname, new_group_id)
    else:
        error_message = 'The name of new group is needed'
    return start_page(error_message)

@route('/<group_id:re:\d*>')
#@route('/<group_id:re:\d*>/<ip_address:re:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}>')
#def show_statistic(group_id, ip_address=''):
def show_statistic(group_id):
    if request.query.action:                                                                                                                  
        if request.query.action == "delete_group" and request.query.group_id:                                                               
                group_id = int(request.query.group_id)
                delete_group_from_monitoring(group_id)
                return redirect('/')                                                                                                 
        elif request.query.action == "delete_ip" and request.query.group_id and request.query.ip_addr:                                        
                group_id = int(request.query.group_id)
                ip_address = request.query.ip_addr
                delete_ip_from_monitoring(group_id, ip_address)
                return redirect(request.path)
        else:
                return redirect(request.path)
    group_info = []
    group_id_name_comment = get_group_and_comment_list(group_id=group_id)
    if not group_id_name_comment:
        return redirect(request.path)
    else:
        group_info.append(group_id_name_comment[0])
    group_ip_list = get_group_ip_list(group_id)
    group_info.append(group_ip_list)
    ip_address = request.query.get('ip')
    if ip_address:
        if not check_format_ip(ip_address):
            return redirect('/'+group_id)
    
    date = request.query.get('show-date')
    if date and check_format_date(date):
        monitoring_date = date
    else:
        monitoring_date = time.strftime("%d.%m.%Y", time.localtime())
    date_list = get_date_list_when_ip_monitored(ip_address)
    if monitoring_date in date_list:
        ip_statistic = get_statistic_ip_day(ip_address, monitoring_date)
    else:
        ip_statistic = []

    hour = request.query.get('hour')
    if hour:
        ip_statistic_hour = get_statistic_ip_hour(ip_address, monitoring_date, hour)
    else:
        ip_statistic_hour = []

    return template('ip_statistic.html',
                    group_info=group_info, # group_info = [(group_id, group_name, group_comment), [(ip, hostname), ...]]
                    ip_statistic=ip_statistic, 
                    ip_statistic_hour = ip_statistic_hour,
                    monitoring_date=monitoring_date, 
                    ip_address=ip_address,
                    date_list=date_list,
                    hour=hour,
                    page_title='Statistics - Pinger')

@route('/<group_id:re:\d*>/edit')
def edit_group(group_id):
    group_id = int(group_id)
    group_and_comment = get_group_and_comment_list(group_id=group_id) # it returns [(group_id, group_name, group_comment)]
    group_and_comment = group_and_comment[0]    # it makes (group_id, group_name, group_comment)
    if not group_and_comment:
        return redirect('/')
    return template('edit_group.html', 
                    group_and_comment=group_and_comment,
                    page_title='Edit Comment - Pinger')

@route('/<group_id:re:\d*>/edit', method='POST')
def edit_group_save(group_id):
    group_id = int(group_id)
    group_comment = request.forms.get('edit-group-comment').decode('utf-8')
    update_group_comment(group_id, group_comment)
    return redirect('/')
    

@error(404)
def error404(error):
    return '<h1>Page not found. Error 404.</h1> <span>path: ' + request.path + '</span>' 

run(port=8888, debug=True, reload=True)
#run(server='cgi')
#run(host='192.168.7.49', port=8080, debug=True, reload=True)

###################
###################
