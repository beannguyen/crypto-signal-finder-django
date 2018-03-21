import logging
from best_django.settings import DEBUG

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def write_log(msg):
    if DEBUG:
        logger.debug(msg)
