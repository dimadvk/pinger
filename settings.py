#!/usr/bin/env python
#
# Name of database for storing data
db_name='db_pinger.sqlite3'

# Path to ping utility
ping = '/bin/ping' 

# Monitoring results older then "days_results_obselete" will be removed from base
day_results_obselete = '30'

# Set scopes of warning level. Color of row in monitoring results depends on that.
# if warning_packetloss_level1 < packet_loss < warning_packetloss_level2
#	than light_red line color
# if packet_loss > warning_packetloss_level2
#   than red line color
warning_packetloss_level1 = 0
warning_packetloss_level2 = 6

# IP from this networks cannot be added for monitoring
blocked_IpRangeList = iptools.IpRangeList('224.0.0.0/4', '255.255.255.255')
