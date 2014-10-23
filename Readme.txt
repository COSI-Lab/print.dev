New Print Server Development Progress:

10/30/13
- Made a github to share info
- Discussed goals
- Began website front-end in html/javascript
- Began research on server basics

11/14/13
- Began research on CUPS, python, and mysql
- Got a basic website working
- Designed a basic map of steps to take

Sometime between 11/14/13 and 10/23/14
 - created print.dev server
 - installed many packages (listed on docs)
 - updated server
 - manually installed pykota
 - initialized a database in pykota
 - configured CUPS
 - found admin page for CUPS
 - added new printer to admin page for CUPS
 - installed uWSGI and Flask to host webpage
 - wrote python script to manage basic backend functionality with webpage

10/23/14
 - Began permanently hosting webpage
 - Edited /srv/wsgi/print/print.py and conf.py to include printing a test page
 - Printed a test page from website through CUPS
 - Implemented pykota backend for user quota management and initialized test account
 - Printed a test page using pykota
 - Updated docs
