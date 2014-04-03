#!/bin/bash
./openerp-server -r postgres &
sleep 5
OPENERP_PID=$!
python ./create_db.py
sleep 10
kill $OPENERP_PID
