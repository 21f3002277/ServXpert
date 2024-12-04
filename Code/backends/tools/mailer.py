import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from config import Config


def send_email(to_email, subject, body):
    """
    Sends an email with the specified subject and HTML body.
    """
    sender_email = Config.MAIL_USERNAME
    sender_password = Config.MAIL_PASSWORD
    smtp_server = Config.MAIL_SERVER
    smtp_port = Config.MAIL_PORT

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    # Attach the email body to the message
    msg.attach(MIMEText(body, "html"))

    try:
        # Connect to the server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Use TLS
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")


def send_email_with_attachment(to_email, subject, body, attachment_path, attachment_filename):
    """
    Sends an email with an attachment.
    """
    sender_email = Config.MAIL_USERNAME
    sender_password = Config.MAIL_PASSWORD
    smtp_server = Config.MAIL_SERVER
    smtp_port = Config.MAIL_PORT

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    # Attach the email body to the message
    msg.attach(MIMEText(body, "plain"))

    # Attach the file
    try:
        with open(attachment_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename={attachment_filename}')
            msg.attach(attachment)
    except FileNotFoundError:
        print(f"Attachment file not found: {attachment_path}")
        return

    try:
        # Connect to the server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Use TLS
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Email with attachment sent to {to_email}")
    except Exception as e:
        print(f"Error sending email with attachment: {e}")


def send_email_with_csv(to_email, csv_data):
    sender_email = Config.MAIL_USERNAME
    sender_password = Config.MAIL_PASSWORD
    smtp_server = Config.MAIL_SERVER
    smtp_port = Config.MAIL_PORT
    try:
        # Create the email message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = to_email
        message['Subject'] = "Closed Service Requests Export"

        # Email body
        body = "The closed service requests have been exported successfully. Find the CSV attached."
        message.attach(MIMEText(body, 'plain'))

        # Attach CSV
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(csv_data.getvalue().encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename="closed_service_requests.csv")
        message.attach(attachment)

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, sender_email, message.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
