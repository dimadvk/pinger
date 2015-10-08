#!/usr/bin/env python
# coding:utf-8

from bottle import run, route, HTTPError, static_file, template, request, redirect
import iptools
import time
import sqlite3
import os
import re
from settings import db_name, warning_packetloss_level1, warning_packetloss_level2

# db - absolute path to database file.
path_to_script = os.path.dirname(__file__)
db = os.path.join(path_to_script, db_name)
# IP from this networks cannot be added for monitoring
blocked_networks = iptools.IpRangeList('224.0.0.0/4', '255.255.255.255')

#########

def executeSQL(statement, args=''):
    """
    Execute SQL-statement, return result.
    Next format of oraguments is required: 
      'statement' - sql-statement as a string, 'args' - tuple.
    """
    with sqlite3.connect(db) as connection:
        curs = connection.cursor()
        # Foreign key constraints are disabled by default, 
        # so must be enabled separately for each database connection
        curs.execute('PRAGMA FOREIGN_KEYS=ON')
        curs.execute(statement, args)
    return curs.fetchall()

def get_statistic_ip_day(ip, date):
    """
    Get a day monitoring statistic for ip
    [[hour, sent, received, loss_percent], ... ]
    """
    get_results_ip = executeSQL('''
                        SELECT strftime('%H', date_time),
                               sum(sent),
                               sum(received),
                               (sum(sent)-sum(received))*100/sum(sent) as loss_percent
                            FROM ping_results WHERE ip=? and date(date_time)=? 
                            GROUP BY strftime('%H', date_time)
                            ''', (ip, date))
    statistic_ip = []
    for row in get_results_ip:
        row = list(row)
        hour_num = row[0]
        row.append(hour_num)
        # make hour: '01' >> '1:00-2:00'
        row[0] = row[0]+':00-'+str(int(row[0])+1)+':00' 
        packetloss = int(row[3])
        if packetloss ==0:
            row.append('')
        elif warning_packetloss_level1 < packetloss < warning_packetloss_level2:
            row.append('warning_packetloss_level1')
        elif packetloss >= warning_packetloss_level2:
            row.append('warning_packetloss_level2')
        statistic_ip.append(row)
    return statistic_ip

def get_statistic_ip_hour(ip, date, hour):
    """
    Get a monitoring statistic for ip for specified hour
    [ [hour, minute, sent, received, loss_percent], ... ]
    """
    get_results_ip = executeSQL('''
                        SELECT strftime('%H', date_time),
                               strftime('%M', date_time),
                               sent,
                               received,
                               (sent - received)*100/sent as loss_percent
                            FROM ping_results 
                            WHERE ip=? 
                                  and date(date_time)=? 
                                  and strftime('%H', date_time)=?
                            ''', (ip, date, hour))
    # make a list with results
    statistic_ip_hour = []
    for row in get_results_ip:
        row = list(row)
        packetloss = int(row[4])
        if packetloss ==0:
            row.append('')
        elif warning_packetloss_level1 < packetloss < warning_packetloss_level2:
            row.append('warning_packetloss_level1')
        elif packetloss >= warning_packetloss_level2:
            row.append('warning_packetloss_level2')
        statistic_ip_hour.append(row)
    return statistic_ip_hour


def get_date_list_when_ip_monitored(ip_address):
    """
    Return list of dates when ip where monitored 
    [ 'date_1', 'date_2', ... ]
    """
    date_list = executeSQL('''
                    SELECT date(date_time) 
                        FROM ping_results 
                        WHERE ip=? 
                        GROUP BY date(date_time)
                        ORDER BY date(date_time)
                        ''', (ip_address, ))
    # make [ (date1,), ... ] >> [ date1, ... ]
    date_list = [date[0] for date in date_list]
    return date_list

def get_group_and_comment_list():
    """
    Return group list from base
    [(id_1, group1, comment1), (id_2, group2, comment2), ...]
    """
    group_list = executeSQL('''
                    SELECT id, group_name, group_comment
                        FROM group_list order by id DESC''')
    return group_list

def get_group_name_and_comment(group_id):
    """
    Return tuple with group name and comment for specified group_id: 
    (group_id, group_name, group_comment)
    If there is no group with that id return empty list
    """
    group_name_and_comment = executeSQL('''
                                SELECT id, group_name, group_comment
                                    FROM group_list WHERE id=?
                                    ''', (group_id, ))
    # check if group_name_and_comment is not empty, extract tuple from list.
    if group_name_and_comment:
        group_name_and_comment = group_name_and_comment[0]
    return group_name_and_comment

def update_group_comment(group_id, new_group_comment):
    """
    Update comment for selected group
    """
    executeSQL('''UPDATE group_list 
                    SET group_comment=? 
                    WHERE id=?''', (new_group_comment, group_id))

def get_group_ip_list(group_id):
    """
    It returns list [(ip1, hostname1), (ip2, hostname2) ... ]
    """
    group_ip_list = executeSQL('''SELECT ip, hostname 
                                    FROM ip_list 
                                    WHERE group_id=?''', (group_id, ))
    return group_ip_list

def add_ip_for_monitoring(ip_address, hostname, group_id):
    """
    Add IP to group with id group_id
    """
    executeSQL('''INSERT INTO ip_list (ip, hostname, group_id) 
                    VALUES (?, ?, ?)''', (ip_address, hostname, group_id))

def add_group(group_name, group_comment):
    """
    Add new group to databse, return its group_id
    """
    with sqlite3.connect(db) as connection:
        curs = connection.cursor()
        curs.execute('''INSERT INTO group_list (group_name, group_comment) 
                            VALUES (?, ?)''', (group_name, group_comment))
        # get 'id' of group that where just been made
        new_group_id = curs.lastrowid
    return new_group_id

def delete_group_from_monitoring(group_id):
    """
    Delete from monitoring all IP in group with id 'group_id'
    than delete group.
    """
    executeSQL('DELETE FROM ip_list WHERE group_id=?', (group_id, ))
    executeSQL('DELETE FROM group_list WHERE id=?', (group_id, ))

def delete_ip_from_monitoring(group_id, ip_address):
    """
    Delete IP from group with id group_id
    """
    executeSQL('''DELETE FROM ip_list 
                    WHERE ip=? and group_id=?''', (ip_address, group_id))

def check_format_ip(ip):
    """
    Check if IP could be added for monitoring
    """
    if not re.match('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return False
    elif ip in blocked_networks:
        return False
    else:
        return True

def check_format_date(date):
    """
    Check format of date string
    """
    if re.match('([12][0-9][0-9][0-9])\-(1[012]|0[1-9])\-(3[01]|2[0-9]|[01][0-9])$', date):
        return 1
    else:
        return 0


#########

# for static files
@route('/static/<filename>')
def static_css(filename):
    return static_file(filename, root='static/css/')

# / - start page
@route('/')
def start_page(error_message=''):
    monitoring_list = []
    # get [(group_id, group_name, group_comment), ...]
    group_list = get_group_and_comment_list() 
    
    # construct list # [ [(group_id, group_name, group_comment), [(ip, hostname), ...]], ... ]
    # for rendering html-page 
    for group in group_list:
        group_id = group[0]
        # get [(ip, hostname), ...] for group in group_list
        group_ip_list = get_group_ip_list(group_id)
        monitoring_list.append([group, group_ip_list]) 
    return template('start.html',
                    group_list = group_list,
                    monitoring_list = monitoring_list,
                    error_message=error_message,
                    page_title = 'Pinger')

# / - start page with POST method
@route('/', method='POST')
def start_page_post():
    action = request.forms.get('action')

    # only one of three kind of 'action' could be accepted:
    # 'add_new_item', 'delete_group', 'delete_ip'
    if action == 'add_new_item':
        error_message = ''
        ip_addr = request.forms.get('ip')
        # remove leading and trailing whitespace
        ip_addr = ip_addr.strip()
        # .decode('utf-8') - it needs for sqlite3 accepting cyrillic symbols
        hostname = request.forms.get('hostname').decode('utf-8') 
        selected_group_id = request.forms.get('select_group')
        new_group_name = request.forms.get('new_group_name')
        new_group_comment = request.forms.get('group_comment')

        # user can only chose one of existed groups or enter a name for new group
        if selected_group_id:
            selected_group_id = int(selected_group_id)
            group_ip_list = get_group_ip_list(selected_group_id) 
            # make [ (ip1, hostname1), ... ] >> [ ip1, ... ]
            group_ip_list = [x[0] for x in group_ip_list] 
            if not check_format_ip(ip_addr):
                error_message = "IP {} cannot not be added".format(ip_addr)
            elif ip_addr in group_ip_list:
                error_message = 'IP "'+ ip_addr +'" already exists in that group'
            else:
                add_ip_for_monitoring(ip_addr, hostname, selected_group_id)
        # if user enter a new group name than create new group
        elif new_group_name: 
            new_group_name = new_group_name.decode('utf-8')
            #get list of group names
            group_list = get_group_and_comment_list()
            group_name_list = [x[1] for x in group_list]

            if new_group_name in group_name_list:
                error_message = 'the group with the name "'+ new_group_name + '" already exists'
            elif not check_format_ip(ip_addr):
                error_message = 'wrong format of IP'
            else:
                if new_group_comment:
                    new_group_comment = new_group_comment.decode('utf-8')
                else:
                    new_group_comment = '-'
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

# /<group_id> - open a page for one group
@route('/<group_id:re:\d*>')
def show_statistic(group_id):
    # group_info - a list with data for rendering html-page
    # format: [ (group_id, group_name, group_comment), [ (ip, hostname), ... ] ]
    group_info = []
    group_id_name_comment = get_group_name_and_comment(group_id)

    # if group_id_name_comment is empty - raise an error 404
    if not len(group_id_name_comment):
        raise HTTPError(404, "Not found: " + repr(request.path))

    group_info.append(group_id_name_comment)

    # get list of IP for specified group
    group_ip_list = get_group_ip_list(group_id)
    group_info.append(group_ip_list)
    ip_address = request.query.get('ip')

    # if IP is specified but in wrong format than redirect to the group page
    if ip_address:
        if not check_format_ip(ip_address):
            return redirect('/'+group_id)

    date = request.query.get('show-date')
    
    # If 'date' is specified in right format than
    # show monitoring results for that day.
    # Show result for current system date in other way.
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
                    group_info=group_info,
                    ip_statistic=ip_statistic,
                    ip_statistic_hour = ip_statistic_hour,
                    monitoring_date=monitoring_date,
                    ip_address=ip_address,
                    date_list=date_list,
                    hour=hour,
                    page_title='Statistics - Pinger')

# '/<group_id>' with POST method
@route('/<:re:\d*>', method='POST')
def group_page_post():
    action = request.forms.get('action')
    # There's only one of two kinds of action could be accepted:
    # 'delete_group', or 'delete_ip'
    if action == "delete_group":
        group_id = int(request.forms.get('group_id'))
        delete_group_from_monitoring(group_id)
        return redirect('/')
    elif action == "delete_ip":
        group_id = int(request.forms.get('group_id'))
        ip_address = request.forms.get('ip')
        delete_ip_from_monitoring(group_id, ip_address)
        return redirect(request.path)

# /edit/<group_id> - edit comment for group
@route('/edit/<group_id:re:\d*>')
def edit_group(group_id):
    group_id = int(group_id)
    # get (group_id, group_name, group_comment)
    group_and_comment = get_group_name_and_comment(group_id)

    #if no group found for specified group_id than redirect to '/'
    if not group_and_comment:
        return redirect('/')

    return template('edit_group.html',
                    group_and_comment=group_and_comment,
                    page_title='Edit Comment - Pinger')

# /edit/<group_id> - save new comment after edit and go to '/'
@route('/edit/<group_id:re:\d*>', method='POST')
def edit_group_save(group_id):
    group_id = int(group_id)
    group_comment = request.forms.get('edit-group-comment').decode('utf-8')
    update_group_comment(group_id, group_comment)
    return redirect('/')


run(port=8888, debug=True, reload=True)
#run(server='cgi')
#run(host='192.168.7.49', port=8080, debug=True, reload=True)
#run(host='195.234.68.26', port=8080, debug=True, reload=True)

###################
