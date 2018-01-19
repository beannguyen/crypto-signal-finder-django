import uuid

from best_django.settings import EMAIL_HOST_USER, HOME_URL
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
