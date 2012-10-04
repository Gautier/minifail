import smtplib
from email.mime.text import MIMEText

class SMTPNotifier(object):
    def __init__(self, host, port, recipient, from_email):
        self.host = host
        self.port = port
        self.recipient = recipient
        self.from_email = from_email

    def notifiy(self, subject, body):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = self.recipient

        connection = smtplib.SMTP(host=self.host, port=self.port)
        connection.sendmail(self.from_email, [self.recipient], msg.as_string())
        connection.quit()
