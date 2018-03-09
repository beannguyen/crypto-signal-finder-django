import psycopg2
import traceback
import time

try:
    conn = psycopg2.connect("dbname='bsf_test1' user='killer' host='localhost' password='Th3NeWorld@@@1893'")
    cur = conn.cursor()
    sql = "﻿SELECT pg_terminate_backend(pid) " \
          "FROM pg_stat_activity " \
          "WHERE datname = 'bsf_test1' " \
          "AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)', 'disabled')" \
          "AND pid <> pg_backend_pid()"

    while True:
        cur.execute(sql)
        time.sleep(1 * 60)
except:
    traceback.print_exc()
