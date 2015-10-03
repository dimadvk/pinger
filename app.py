#!/usr/bin/env python
# coding:utf-8

#
# create table group_list(id integer primary key AUTOINCREMENT, group_name text, group_comment text);
# create table ip_list (id INTEGER PRIMARY KEY autoincrement, ip text, hostname text, group_id integer);
#
# select hour, ip, sum(sent), sum(received), (sum(sent)-sum(received))*100/sum(sent) as loss from ping_results  group by ip, hour order by ip;



##### To Do List #####
"""
- add checkin is database 'pinger_db.sqlite3' exists when server starts.
    If no 'pinger_db.sqlite3' exists initialize new one.
- remome monitoring results older than 2 month


"""
######################


from bottle import run, route, HTTPError, static_file, template, request, redirect
import time
import datetime
import sqlite3
import os
import re
from settings import db_name

path_to_script = os.path.dirname(__file__)
db = os.path.join(path_to_script, db_name)

#########

def executeSQL(statement, args=''):
    """
    execute SQL-statement, return result.
    Next type of oraguments is required: 
      'statement' - sql-statement as a string, 'args' - tuple.
    """
    with sqlite3.connect(db) as connection:
        curs = connection.cursor()
        # Foreign key constraints are disabled by default, so must be enabled separately for each database connection
        curs.execute('PRAGMA FOREIGN_KEYS=ON')
        curs.execute(statement, args)
    return curs.fetchall()

def get_statistic_ip_day(ip, date):
    """get a day monitoring statistic for ip
    [[hour, sent, received, loss_percent], ... ]"""
    get_results_ip = executeSQL('''SELECT strftime('%H', date_time),
                                          sum(sent),
                                          sum(received),
                                          (sum(sent)-sum(received))*100/sum(sent) as loss_percent
                                            from ping_results where ip=? and date(date_time)=? group by strftime('%H', date_time)''', (ip, date))
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
    """get a monitoring statistic for ip for specified hour
    [[hour, minute, sent, received, loss, warning_level], ... ]"""
    get_results_ip = executeSQL('''SELECT strftime('%H', date_time),
                                          strftime('%M', date_time),
                                          sent,
                                          received,
                                          (sent - received)*100/sent as loss_percent
                                              from ping_results where ip=? and date(date_time)=? and strftime('%H', date_time)=?''', (ip, date, hour))
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
    """
    Return list of dates when ip where monitored 
    [ 'date_1', 'date_2', ... ]
    """
    date_list = executeSQL('''SELECT date(date_time) from ping_results where ip=? group by date(date_time)''', (ip_address, ))
    date_list = [date[0] for date in date_list] # it returns [ date1, date2, ... ]
    date_list.sort(key=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
    return date_list

def get_group_and_comment_list():
    """
    return group list from base
    [(id_1, group1, comment1), (id_2, group2, comment2), ...]
    """
    group_list = executeSQL('''SELECT id,
                                      group_name,
                                      group_comment
                                        from group_list order by id DESC''')
    return group_list

def get_group_name_and_comment(group_id):
    """
    return tuple with group name and comment for specified group_id: 
    (group_id, group_name, group_comment)
    """
    group_name_and_comment = executeSQL('''SELECT id,
                                      group_name,
                                      group_comment
                                        from group_list where id=?''', (group_id, ))
    # check if group_name_and_comment is not empty, extract tuple from list.
    if group_name_and_comment:
        group_name_and_comment = group_name_and_comment[0]
    return group_name_and_comment

def update_group_comment(group_id, new_group_comment):
    """update comment for one group"""
    executeSQL('update group_list set group_comment=? where id=?', (new_group_comment, group_id))

def get_group_ip_list(group_id):
    """it returns list [(ip, hostname), (ip2, hostname2) ... ]"""
    group_ip_list = executeSQL('SELECT ip, hostname from ip_list where group_id=?', (group_id, ))
    return group_ip_list

def add_ip_for_monitoring(ip_address, hostname, group_id):
    executeSQL('INSERT INTO ip_list (ip, hostname, group_id) values (?, ?, ?)', (ip_address, hostname, group_id))

def add_group(group_name, group_comment):
    executeSQL('INSERT INTO group_list (group_name, group_comment) values (?, ?)', (group_name, group_comment))
    new_group_id = executeSQL('SELECT seq FROM sqlite_sequence where name="group_list"')
    new_group_id = new_group_id[0][0] # it makes: [(id, )] >> id
    return new_group_id

def delete_group_from_monitoring(group_id):
    executeSQL('DELETE FROM ip_list where group_id=?', (group_id, ))
    executeSQL('DELETE FROM group_list where id=?', (group_id, ))

def delete_ip_from_monitoring(group_id, ip_address):
    executeSQL('DELETE FROM ip_list where ip=? and group_id=?', (ip_address, group_id))

def check_format_ip(ip):
    if re.match('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return 1
    else:
        return 0

def check_format_date(date):
    if re.match('([12][0-9][0-9][0-9])\-(1[012]|0[1-9])\-(3[01]|2[0-9]|[01][0-9])$', date):
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
def start_page_post():
    action = request.forms.get('action')
    if action == 'add_new_item':
        error_message = ''
        ip_addr = request.forms.get('ip')
        ip_addr = re.sub('[ ]', '', ip_addr) # just clear any ' ' from string
        hostname = request.forms.get('hostname').decode('utf-8') # .decode('utf-8') - it needs for sqlite3 accepting cyrillic symbols
        selected_group_id = request.forms.get('select_group')
        new_group_name = request.forms.get('new_group_name')
        new_group_comment = request.forms.get('group_comment')
        if selected_group_id: # if user want to add ip with one of existing group
            selected_group_id = int(selected_group_id)
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
                add_ip_for_monitoring(ip_addr, hostname, new_group_id)
        else:
            error_message = 'The name of new group is needed'
        return start_page(error_message)

    elif action == "delete_group":
        group_id = int(request.forms.get('group_id'))
        delete_group_from_monitoring(group_id)
        return redirect('/')
    elif action == "delete_ip":
        group_id = int(request.forms.get('group_id'))
        ip_address = request.forms.get('ip')
        delete_ip_from_monitoring(group_id, ip_address)
        return redirect('/')

# /<number>
@route('/<group_id:re:\d*>')
def show_statistic(group_id):
    group_info = []
    group_id_name_comment = get_group_name_and_comment(group_id)

    # if group_id_name_comment is empty - raise an error 404
    if not len(group_id_name_comment):
        raise HTTPError(404, "Not found: " + repr(request.path))

    group_info.append(group_id_name_comment)    
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
        monitoring_date = time.strftime("%Y-%m-%d")
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

@route('/<:re:\d*>', method='POST') # '/<group_id>'
def group_page_post():
    action = request.forms.get('action')
    if action == "delete_group":
        group_id = int(request.forms.get('group_id'))
        delete_group_from_monitoring(group_id)
        return redirect('/')
    elif action == "delete_ip":
        group_id = int(request.forms.get('group_id'))
        ip_address = request.forms.get('ip')
        delete_ip_from_monitoring(group_id, ip_address)
        return redirect(request.path)


@route('/edit/<group_id:re:\d*>')
def edit_group(group_id):
    group_id = int(group_id)
    group_and_comment = get_group_and_comment_list(group_id=group_id) # it returns [(group_id, group_name, group_comment)]
    group_and_comment = group_and_comment[0]    # it makes (group_id, group_name, group_comment)
    if not group_and_comment:
        return redirect('/')
    return template('edit_group.html',
                    group_and_comment=group_and_comment,
                    page_title='Edit Comment - Pinger')

@route('/edit/<group_id:re:\d*>', method='POST')
def edit_group_save(group_id):
    group_id = int(group_id)
    group_comment = request.forms.get('edit-group-comment').decode('utf-8')
    update_group_comment(group_id, group_comment)
    return redirect('/')


#@error(404)
#def error404(error):
#    return '<h1>Page not found. Error 404.</h1> <span>path: ' + request.path + '</span>'

#run(port=8888, debug=True, reload=True)
#run(server='cgi')
#run(host='192.168.7.49', port=8080, debug=True, reload=True)
run(host='195.234.68.26', port=8080, debug=True, reload=True)

###################
