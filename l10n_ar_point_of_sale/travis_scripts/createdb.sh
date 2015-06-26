#!/bin/bash
$HOME/openerp-7.0/openerp-server --xmlrpc-port=8069 --logfile=$HOME/openerp.log -r openerp -w p4s5W0rD! &
sleep 10
OPENERP_PID=$!
python travis_scripts/create_db.py
sleep 10
kill $OPENERP_PID
