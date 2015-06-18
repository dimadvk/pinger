#!/usr/bin/python

import os, bottle, sys
sys.path = ['/var/www/pinger/pinger/'] + sys.path
os.chdir(os.path.dirname(__file__))
import app
application = bottle.default_app()
