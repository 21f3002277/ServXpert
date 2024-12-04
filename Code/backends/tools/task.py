from datetime import datetime
import email
from sqlalchemy.sql import extract
from .workers import celery
from models import *
from celery.schedules import crontab
from flask import render_template
from tools.mailer import send_email, send_email_with_attachment
import pdfkit
import os
import platform

# PDFKit configuration based on OS
if platform.system() == 'Windows':
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe')
else:
    config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')

# PDFKit configuration
PDF_OUTPUT_DIR = "/reports"  # Update this path to a valid directory
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)  # Ensure the directory exists



@celery.task
def send_welcome_note_customer(email, firstname):
    """
    Sends a welcome email to a customer.
    """
    html_content = render_template('customer_welcome_note.html', firstname=firstname)
    subject = "Welcome to ServXperts!"
    send_email(email, subject, html_content)
    print(f"Welcome email sent to {email}")


@celery.task
def send_welcome_note_professional(email, firstname):
    """
    Sends a welcome email to a professional.
    """
    html_content = render_template('professional_welcome_note.html', firstname=firstname)
    subject = "Welcome to ServXperts!"
    send_email(email, subject, html_content)
    print(f"Welcome email sent to {email}")

@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(crontab(hour = 11, minute= 40), send_daily_email.s(), name=" every day at 11:40 AM")
    sender.add_periodic_task(crontab(hour=11, minute=45, day_of_month=29),monthly_activity_report.s(),name="Send monthly activity report")


def get_pending_requests():
    """
    Fetch all pending service requests grouped by service professionals.
    Returns a dictionary where keys are ServiceProfessional objects and values are lists of ServiceRequest objects.
    """
    try:
        pending_requests = (
            ServiceRequest.query
            .filter_by(status="requested")  # Only fetch requests with 'requested' status
            .join(ServiceProfessional, ServiceRequest.professional_id == ServiceProfessional.id)
            .options(db.joinedload(ServiceRequest.professional))  # Optimize query with eager loading
            .all()
        )
        professionals_with_requests = {}
        for request in pending_requests:
            professional = request.professional
            if professional not in professionals_with_requests:
                professionals_with_requests[professional] = []
            professionals_with_requests[professional].append(request)
        return professionals_with_requests
    except Exception as e:
        print(f"Error fetching pending requests: {e}")
        return {}

@celery.task
def send_daily_email():
    """
    Sends daily reminders to service professionals with pending service requests.
    """
    try:
        # Fetch pending requests grouped by professionals
        pending_requests_by_professional = get_pending_requests()

        if not pending_requests_by_professional:
            print("No pending requests to process.")
            return

        for professional, pending_requests in pending_requests_by_professional.items():
            # Ensure the professional has an associated User and email
            user = professional.user  # Fetch the User object associated with the ServiceProfessional
            
            if not user or not user.email:
                print(f"Skipping professional {professional.fullname}: No email associated with User.")
                continue

            # Generate the email content
            try:
                

                # Send the email
                send_email(
                    to_email=user.email,  # Access email from the User table
                    subject="Daily Reminder: Pending Service Requests",
                    body= render_template('daily_reminders.html',
                                                professional_name=professional.fullname, 
                                                requests_list=pending_requests, 
                                                current_year=datetime.now().year)
                )
                

                print(f"Daily Reminder email sent to {professional.fullname} at {user.email}")

            except Exception as email_exception:
                print(email_exception)
                print(f"Error sending email to {professional.fullname}: {email_exception}")

    except Exception as e:
        print(f"Error during daily email task: {e}")

@celery.task
def monthly_activity_report():
    """
    Generates and sends monthly activity reports for all customers.
    """
    today = datetime.today()
    #month = today.month - 1  if today.month > 1 else 12  # Last month
    month = today.month  if today.month > 1 else 12  # This month for demo to viva
    year = today.year if today.month > 1 else today.year - 1

    customers = Customer.query.all()

    for customer in customers:
        try:
            # Retrieve bookings for the customer in the last month
            bookings = Bookings.query.filter(
                Bookings.customer_id == customer.id,
                extract('month', Bookings.booking_date) == month,
                extract('year', Bookings.booking_date) == year
            ).all()
            print(bookings)

            # Prepare report data
            report_data = [
                {
                    'service_name': booking.service.name,
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                    'status': booking.status,
                    'total_amount': booking.total_amount,
                    'professional': booking.professional.fullname if booking.professional else 'N/A',
                    'address': f"{booking.address.location}, {booking.address.city}, {booking.address.state}, {booking.address.zip_code}"
                } for booking in bookings
            ]

            # Generate PDF report
            html = render_template('monthly_report.html', customer=customer,email=customer.user.email, report_data=report_data, month=month, year=year)
            pdf_filename = f"monthly_report_{customer.id}_{month}_{year}.pdf"
            pdf_path = f"/reports/{pdf_filename}"  # Update path as per your environment
            pdfkit.from_string(html, pdf_path)

            # Send the report via email
            send_email_with_attachment(
                to_email=customer.user.email,
                subject="Your Monthly Activity Report",
                body=f"Dear {customer.fullname},\n\nPlease find your activity report for the month attached.",
                attachment_path=pdf_path,
                attachment_filename=pdf_filename
            )
            print(f"Monthly Activity Report email sent to {customer.fullname} at {customer.user.email}")
        except Exception as e:
            print(f"Failed to process monthly report for {customer.fullname} ({customer.user.email}): {str(e)}")

@celery.task
def export_service_requests(csv_data):
    
    try:
        output_path = 'service_requests_export.csv'
        
        # Save to a file
        with open(output_path, 'w') as file:
            file.write(csv_data)

        # Email details
        admin_email = 'vikashpr128@gmail.com'  # Replace with the admin's email address
        subject = "Service Requests Export Completed"
        body = "The service requests export has been completed. Please find the CSV attached."
        filename = f"{admin_email}.csv"
        send_email_with_attachment(admin_email, subject, body, output_path, filename)
        print(f"email notification with attachment sent to {admin_email}")

    except Exception as e:
        print(f"Error during batch job: {e}")




