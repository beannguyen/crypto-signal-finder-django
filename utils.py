import uuid

from best_django.settings import EMAIL_HOST_USER, HOME_URL, STT_ACCOUNT_ACTIVATED, STT_ACCOUNT_UNPAID, STT_ACCOUNT_PENDING, STT_ACCOUNT_BANNED, STT_ACCOUNT_OVERDUE
from django.core.mail import EmailMessage


def generate_ref(length):
    return uuid.uuid4().hex[:length].upper()


def send_mail(subject, to, html_content):
    from_email = EMAIL_HOST_USER
    msg = EmailMessage(subject, html_content, from_email, [to])
    msg.content_subtype = "html"
    msg.send()


def generate_email_verification_link(username, code):
    return '{}/#/verification/{}/{}'.format(HOME_URL, username, code)


def generate_reset_pwd_link(username, code):
    return '{}/#/auth/reset-pwd/{}/{}'.format(HOME_URL, username, code)


def get_user_status_name(stt):
    if stt == STT_ACCOUNT_ACTIVATED:
        return 'Activated'
    if stt == STT_ACCOUNT_UNPAID:
        return 'Unpaid'
    if stt == STT_ACCOUNT_PENDING:
        return 'Waiting'
    if stt == STT_ACCOUNT_BANNED:
        return 'Banned'
    if stt == STT_ACCOUNT_OVERDUE:
        return 'Overdue'
