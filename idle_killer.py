import psycopg2
import traceback
import time
import subprocess

conn = psycopg2.connect("dbname='bsf_test1' user='killer' host='103.68.81.39' password='Th3NeWorld@@@1893'")


def count_all_activity(cur):
    sql = "select count(*) FROM pg_stat_activity where datname = 'bsf_test1'"
    cur.execute(sql)
    rows = cur.fetchall()
    r = rows[0]
    return r[0]


def restart_worker():
    subprocess.call('pkill -9 -f "/home/bean/miniconda2/envs/py35/bin/celery -A best_django worker"', shell=True)
    subprocess.call('nohup /home/bean/be-signal-finder-django/bin/start_worker.sh > /home/bean/be-signal-finder-django/logs/nohup_worker.out 2>&1&', shell=True)


if __name__ == '__main__':
    try:
        INTERVAL_TIME = 30
        SAFE_CONNECTIONS = 300
        MAX_CONNECTION = 1800

        kill_all_sql = "SELECT pg_terminate_backend(pid) " \
                       "FROM pg_stat_activity " \
                       "WHERE datname = 'bsf_test1' " \
                       "AND usename <> 'killer' " \
                       "AND pid <> pg_backend_pid()"

        sql = "SELECT pg_terminate_backend(pid) " \
              "FROM pg_stat_activity " \
              "WHERE datname = 'bsf_test1' " \
              "AND usename <> 'killer' " \
              "AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)', 'disabled')" \
              "AND pid <> pg_backend_pid()" \
              "AND state_change < current_timestamp - INTERVAL '{}' MINUTE;".format(INTERVAL_TIME - 15)

        # time.sleep(INTERVAL_TIME * 60)

        while True:
            conn = psycopg2.connect("dbname='bsf_test1' user='killer' host='103.68.81.39' password='Th3NeWorld@@@1893'")
            cur = conn.cursor()
            start_time = time.time()
            c = count_all_activity(cur)
            print('All activity: ', c)
            # if SAFE_CONNECTIONS <= c < MAX_CONNECTION:
            #    cur.execute(sql)
            #    restart_worker()
            #    print('killed process after {}s'.format(time.time() - start_time))
            if c >= MAX_CONNECTION:
				cur.execute(sql)
                restart_worker()
                print('killed all process')
            time.sleep(1 * 60)
    except:
        traceback.print_exc()
