import psycopg2
import traceback
import time

conn = psycopg2.connect("dbname='bsf_test1' user='killer' host='localhost' password='Th3NeWorld@@@1893'")


def count_all_activity():
    cur = conn.cursor()
    sql = "select count(*) FROM pg_stat_activity where datname = 'bsf_test1'"
    cur.execute(sql)
    rows = cur.fetchall()
    r = rows[0]
    return r[0]


if __name__ == '__main__':
    try:
        INTERVAL_TIME = 30
        SAFE_CONNECTIONS = 300

        sql = "SELECT pg_terminate_backend(pid) " \
              "FROM pg_stat_activity " \
              "WHERE datname = 'bsf_test1' " \
              "AND usename <> 'killer' " \
              "AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)', 'disabled')" \
              "AND pid <> pg_backend_pid()" \
              "AND state_change < current_timestamp - INTERVAL '{}' MINUTE;".format(INTERVAL_TIME - 15)

        # time.sleep(INTERVAL_TIME * 60)

        while True:
            cur = conn.cursor()
            start_time = time.time()
            c = count_all_activity()
            print('All activity: ', c)
            if c >= SAFE_CONNECTIONS:
                cur.execute(sql)
                print('killed process after {}s'.format(time.time() - start_time))
            time.sleep(5 * 60)
    except:
        traceback.print_exc()
