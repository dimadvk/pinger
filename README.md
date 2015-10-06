# pinger

There are:
- script pinger.py that fetches ip address list from database, makes ping for each ip and save results to database.
- web application app.py for managing monitoring list and viewing monitoring results

How to install and use:

1. clone repository: $ git clone https://github.com/manonduty/pinger
2. go to created directory "pinger" and check file settings.py
3. run "pip install -r requirements.txt"
4. run script initialize_db.py: $ python initialize_db.py <br>
    it creates database pinger_db.sqlite3 (or with the name specified in settings.py)
5. add pinger.py to crontab: <br>
    $ crontab -e <br>
  add string: * * * * * /YourPath/pinger.py <br>
  where /YourPath/ is absolute path to pinger.py on your machine (e.x. /home/User/pinger/pinger.py)
6. run web application to manage ip address list and view monitoring results: $ python app.py
