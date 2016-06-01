# pinger

There are:
- script pinger.py that fetches ip address list from database, makes ping for each ip and save results to database.
- web application app.py for managing monitoring list and viewing monitoring results

# How to install and use<br>

Launch Pinger with following steps: <br>

1. clone repository: $ git clone https://github.com/manonduty/pinger
2. go to created directory "pinger": $ cd pinger/
3. run "pip install -r requirements.txt"(using [virtualenv](http://virtualenv.readthedocs.io/en/stable/) is recomended)
4. add pinger.py to crontab: <br>
    $ crontab -e <br>
  set to execute pinger.py every minute. For example, add the string:<br>
  * * * * *       /usr/bin/python /data/work/virtualenvs/pinger-test/src/pinger/pinger.py<br>
5. run web application to manage ip address list and view monitoring results:
    $ python app.py<br>
6. Go to web-page http://127.0.0.1:8888/ and try to use.


- First running app.py or pinger.py will create a database file in a pinger directory
- At the upper part of the scripts app.py and pinger.py there are some variables that you may change
(name for database, path to ping utility).
