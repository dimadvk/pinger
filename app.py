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
    [[hour, sent, received, loss_percent, warning_packetloss_level], ... ]
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

def get_group_ip_hostname_list(group_id):
    """
    It returns list [(ip1, hostname1), (ip2, hostname2) ... ]
    """
    group_ip_hostname_list = executeSQL('''SELECT ip, hostname 
                                    FROM ip_list 
                                    WHERE group_id=?''', (group_id, ))
    return group_ip_hostname_list

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
    if not re.match('^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$', ip):
        return False
    elif ip in blocked_networks:
        return False
    else:
        return True

def validate(**kwargs):
    result = {}
    for key in kwargs.keys():
        result[key] = False
    
    # checking IP
    if 'ip_address' in kwargs.keys():
        if re.match('^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$', ip):
            if ip not in blocked_networks:
                result['ip_address'] = True
  
    # checking group_id
    if 'group_id' in kwargs.keys():
        check_if_exists = executeSQL('SELECT 1 FROM group_list where id=?', (kwargs['group_id'], ))
        if check_if_exists:
            result['group_id'] = True

    return result


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
        group_ip_hostname_list = get_group_ip_hostname_list(group_id)
        monitoring_list.append([group, group_ip_hostname_list]) 
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
        ip_address = request.forms.get('ip')
        # remove leading and trailing whitespace and check format of IP
        ip_address = ip_address.strip()
        #validate if format of IP is correct
        validate_ip = validate(ip_address=ip_address)
        if not validate_ip['ip_address']:
            error_message = "IP '{}' cannot not be added".format(ip_address)
            return start_page(error_message)

        # .decode('utf-8') - it needs for sqlite3 accepting cyrillic symbols
        hostname = request.forms.get('hostname').decode('utf-8') 
        selected_group_id = request.forms.get('select_group')
        new_group_name = request.forms.get('new_group_name')
        new_group_comment = request.forms.get('group_comment')

        # user can only chose one of existed groups or enter a name for new group
        if selected_group_id:
            validate_group_id = validate(group_id=selected_group_id)
            if not validate_group_id['group_id']:
                return redirect(request.path)

            group_ip_hostname_list = get_group_ip_hostname_list(selected_group_id) 
            # make [ (ip1, hostname1), ... ] >> [ ip1, ... ]
            group_ip_list = [x[0] for x in group_ip_hostname_list] 
            if ip_address in group_ip_list:
                error_message = 'IP "'+ ip_address +'" already exists in that group'
            else:
                add_ip_for_monitoring(ip_address, hostname, selected_group_id)
        # if user enter a new group name than create new group
        elif new_group_name: 
            new_group_name = new_group_name.decode('utf-8')
            #get list of group names
            group_list = get_group_and_comment_list()
            group_name_list = [x[1] for x in group_list]

            if new_group_name in group_name_list:
                error_message = 'the group with the name "'+ new_group_name + '" already exists'
            else:
                if new_group_comment:
                    new_group_comment = new_group_comment.decode('utf-8')
                else:
                    new_group_comment = '-'
                new_group_id = add_group(new_group_name, new_group_comment)
                add_ip_for_monitoring(ip_address, hostname, new_group_id)
        else:
            error_message = 'The name of new group is needed'
        return start_page(error_message)
    # END if action == 'add_new_item':
    elif action == "delete_group":
        group_id = request.forms.get('group_id')
        validate_group_id = validate(group_id=group_id)
        if not validate_group_id['group_id']:
            return redirect(request.path)
        delete_group_from_monitoring(group_id)
        return redirect(request.path)
    elif action == "delete_ip":
        group_id = request.forms.get('group_id')
        ip_address = request.forms.get('ip')
        validate_data = validate(group_id=group_id, ip_address=ip_address)
        if validate_data['group_id'] and validate_data['ip_address']:
            delete_ip_from_monitoring(group_id, ip_address)
        return redirect(request.path)

# /<group_id> - open a page for one group
@route('/<group_id:re:\d*>')
def show_statistic(group_id):
    # group_info - a list with data for rendering html-page
    # format: [ (group_id, group_name, group_comment), [ (ip, hostname), ... ] ]
    group_info = []
    group_id_name_comment = get_group_name_and_comment(group_id)

    # if group_id_name_comment is empty - requested page cannot be shown. 
    if not len(group_id_name_comment):
        raise HTTPError(404, "Not found: " + repr(request.path))

    group_info.append(group_id_name_comment)

    # get list of IP for specified group
    group_ip_hostname_list = get_group_ip_hostname_list(group_id)
    group_info.append(group_ip_hostname_list)
    ip_address = request.query.get('ip')
    # if wrong IP is specified than redirect to group page
    group_ip_list = [x[0] for x in group_ip_hostname_list]
    if ip_address and ip_address not in group_ip_list:
        return redirect('/'+group_id)

    date = request.query.get('show-date')
    # If results for specified 'date' and 'IP' exists in database than
    # show monitoring results for that day.
    # Show result for current system date in other way.
    date_list = get_date_list_when_ip_monitored(ip_address)
    if date in date_list:
        monitoring_date = date
    else:
        monitoring_date = time.strftime("%Y-%m-%d")
    ip_statistic = get_statistic_ip_day(ip_address, monitoring_date)

    # if 'hour' is specified in query
    # show resuls for that hour
    ip_statistic_hour = []
    hour = request.query.get('hour')
    available_hours = [x[0] for x in ip_statistic]
    if hour in available_hours:
        ip_statistic_hour = get_statistic_ip_hour(ip_address, monitoring_date, hour)
    else:
        hour = ''

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
        group_id = request.forms.get('group_id')
        validate_group_id = validate(group_id=group_id)
        if not validate_group_id['group_id']:
            return redirect(request.path)
        delete_group_from_monitoring(group_id)
        return redirect('/')
    elif action == "delete_ip":
        group_id = request.forms.get('group_id')
        ip_address = request.forms.get('ip')
        validate_data = validate(group_id=group_id, ip_address=ip_address)
        if validate_data['group_id'] and validate_data['ip_address']:
            delete_ip_from_monitoring(group_id, ip_address)
        return redirect(request.path)

# /edit/<group_id> - edit comment for group
@route('/edit/<group_id:re:\d*>')
def edit_group(group_id):
    # get (group_id, group_name, group_comment)
    group_id_name_comment = get_group_name_and_comment(group_id)

    #if no group found for specified group_id than redirect to '/'
    if not len(group_id_name_comment):
        raise HTTPError(404, "Not found: " + repr(request.path))

    return template('edit_group.html',
                    group_id_name_comment=group_id_name_comment,
                    page_title='Edit Comment - Pinger')

# /edit/<group_id> - save new comment after edit and go to '/'
@route('/edit/<group_id:re:\d*>', method='POST')
def edit_group_save(group_id):
    group_comment = request.forms.get('edit-group-comment').decode('utf-8')
    update_group_comment(group_id, group_comment)
    return redirect('/')

run(port=8888, debug=True, reloader=True, interval=0.5)
#run(host='192.168.7.49', port=8080, debug=True, reload=True)
#run(host='195.234.68.26', port=8080, debug=True, reload=True)

###################
