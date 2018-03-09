#!/bin/bash

cd /home/bean/be-signal-finder-django
sudo /root/miniconda2/envs/py35/bin/python /root/miniconda2/envs/py35/bin/celery -A best_django worker -l info
