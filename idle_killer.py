import psycopg2
import traceback
import time
import subprocess
import os

conn = psycopg2.connect("dbname='bsf_test1' user='killer' host='103.68.81.39' password='Th3NeWorld@@@1893'")


def count_all_activity(cur):
    sql = "select count(*) FROM pg_stat_activity where datname = 'bsf_test1'"
    cur.execute(sql)
    rows = cur.fetchall()
    r = rows[0]
    return r[0]


def restart_worker():
    # subprocess.call(['sudo', 'pkill', '-9', '-f', '/home/bean/miniconda2/envs/py35/bin/celery -A best_django worker'])
    # subprocess.Popen(['echo', '@nhdeptrai123'])
    # subprocess.call(['sudo', 'pkill', '-9', '-f', '/home/bean/miniconda2/envs/py35/bin/celery --app=best_django.celery:app worker'])
    # subprocess.Popen(['echo', '@nhdeptrai123'])
    # subprocess.call(['echo', '$SUDO_PWD\n'])
    # subprocess.call(['bin/reset_worker.sh'], shell=True)
    # subprocess.call(['bin/start_process.sh'], shell=True)
    os.system('sudo /home/bean/be-signal-finder-django/bin/reset_worker.sh')
    os.system('sudo /home/bean/be-signal-finder-django/bin/start_process.sh')


def kill():
    try:
        INTERVAL_TIME = 30
        SAFE_CONNECTIONS = 300
        MAX_CONNECTION = 1000

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
            c = count_all_activity(cur)
            print('All activity: ', c)
            if c >= MAX_CONNECTION:
                cur.execute(sql)
                time.sleep(5)
                restart_worker()
                print('killed all process')
            time.sleep(1 * 60)
    except:
        traceback.print_exc()


if __name__ == '__main__':
    kill()
    # restart_worker()