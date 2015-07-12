# pinger
This app makes ping for list of ip adresses, collect statistic data and save it to local sqlite3 database. 
There are script pinger.py that fetches ip address list, make ping and save results to database.
It made for linux, so i'm not sure if it works on other OS.
Application requires python package "bottle". To install, run: $ pip install bottle
How to install and use:
1. clone repository: $ git clone https://github.com/manonduty/pinger
2. enter the dir "pinger" and check file settings.py
3. run script initialize_db.py: $ python initialize_db.py -- it creates database pinger_db.sqlite3 (or name specified in settings.py)
4. add pinger.py to crontab: 
  $ crontab -e
  add string: * * * * * <path_to pinger>/pinger.py
  where <path_to pinger> is absolute path to pinger.py on your machine (e.x. /home/User/pinger/pinger.py)
5. run web application to manage ip address list and view monitoring results: $ python app.py
