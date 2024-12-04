from .workers import celery
from .SMS_Sender import send_sms

@celery.task
def send_welcome_sms(customer_name, customer_phone):

    message_body = (
        f"Hi {customer_name}! 👋\n"
        f"Welcome to ServXpert! We're excited to have you join us. 🎉\n\n"
        f"If you have any questions or need assistance, reply to this message or call us at [Your Contact Number].\n\n"
        f"Best regards,\n"
        f"The ServXpert Team"
    )

    send_sms(customer_phone, message_body)
    