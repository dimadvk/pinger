#!/usr/bin/python
# that is for run app.py with apache
import os, bottle, sys
sys.path = ['/var/www/pinger/pinger/'] + sys.path
os.chdir(os.path.dirname(__file__))
import app
application = bottle.default_app()
