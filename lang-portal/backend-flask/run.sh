#!/bin/bash
rm -f words.db
python db/init_db.py
python app.py 