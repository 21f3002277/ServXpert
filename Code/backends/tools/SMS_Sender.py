from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from config import Config
import os

def send_sms(recipient: str, message: str) -> str:
    """
    Sends an SMS message using Twilio's API.

    Args:
        recipient (str): The phone number to send the message to.
        message (str): The text content of the SMS.

    Returns:
        str: Success or error message.
    """
    # Load credentials securely (preferably from environment variables)
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", Config.TWILIO_ACCOUNT_SID)
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", Config.TWILIO_AUTH_TOKEN)
    sender = os.getenv("TWILIO_MOBILE_NO", Config.TWILIO_MOBILE_No)

    # Initialize the Twilio client
    client = Client(account_sid, auth_token)

    try:
        # Send the SMS
        sent_message = client.messages.create(
            to=recipient,
            from_=sender,
            body=message
        )
        print(f"Message sent! SID: {sent_message.sid}")
        return "SMS sent successfully!"

    except TwilioRestException as e:
        # Handle Twilio-specific errors
        print(f"Twilio error: {e.msg}")
        return f"Twilio error: {e.msg}"

    except Exception as e:
        # Handle general errors
        print(f"Failed to send SMS: {str(e)}")
        return f"Failed to send SMS: {str(e)}"
