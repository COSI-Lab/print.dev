#!/bin/bash

# Starts a uwsgi web socket with the app context
sudo uwsgi --master --http :80 --wsgi-file print.py --callable app
