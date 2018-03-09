import psycopg2
import traceback
import time

try:
    INTERVAL_TIME = 10

    conn = psycopg2.connect("dbname='bsf_test1' user='killer' host='localhost' password='Th3NeWorld@@@1893'")
    cur = conn.cursor()
    sql = "﻿SELECT pg_terminate_backend(pid) " \
          "FROM pg_stat_activity " \
          "WHERE datname = 'bsf_test1' " \
          "AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)', 'disabled')" \
          "AND pid <> pg_backend_pid()" \
          "AND state_change < current_timestamp - INTERVAL '{}' MINUTE;".format(INTERVAL_TIME)

    while True:
        cur.execute(sql)
        time.sleep(INTERVAL_TIME * 60)
except:
    traceback.print_exc()
