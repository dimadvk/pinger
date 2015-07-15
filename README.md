# pinger

It made for linux, so i'm not sure if it works on other OS.

There are:
- script pinger.py that fetches ip address list from database, makes ping for each ip and save results to database.
- web application app.py for managing monitoring list and viewing monitoring results

Application requires python package "bottle". To install, run: $ pip install bottle

How to install and use:

1. clone repository: $ git clone https://github.com/manonduty/pinger
2. go to created directory "pinger" and check file settings.py
3. run script initialize_db.py: $ python initialize_db.py <br>
    it creates database pinger_db.sqlite3 (or name specified in settings.py)
4. add pinger.py to crontab: <br>
    $ crontab -e <br>
  add string: * * * * * /YoutPath/pinger.py <br>
  where /YourPath/ is absolute path to pinger.py on your machine (e.x. /home/User/pinger/pinger.py)
5. run web application to manage ip address list and view monitoring results: $ python app.py

Screenshots:
- [image-1](https://github.com/manonduty/images/pinger.png)
- [image-2](https://github.com/manonduty/images/pinger1.png)
