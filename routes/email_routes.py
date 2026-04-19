import html
import json
import os
import re
import urllib.error
import urllib.request
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from flask import jsonify, request
from typing import List

from routes.email_templates import BOOKING_SUMMARY_HTML

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def register_email_routes(app):
    @app.route('/api/email/booking-summary', methods=['POST'])
    def booking_summary_email():
        sender = os.environ["GMAIL_ADDRESS"]
        password = os.environ["GMAIL_PASSWORD"]

        if not sender or not password:
            return jsonify({
                'error': 'Email is not configured (set GMAIL_ADDRESS and GMAIL_PASSWORD on the server).',
            }), 500

        data = request.get_json(silent=True)
        assert data is not None, 'Data does not exists, error'
        form = data.get('form')
        assert form is not None, 'Form data does not exists, error'
        
        to_email = form.get('email').strip()

        if not to_email or not _EMAIL_RE.match(to_email):
            return jsonify({'error': 'A valid email is required in your booking details.'}), 400

        selected_iso = data.get('selectedTimeIso')
        assert selected_iso is not None, 'Selected time ISO is not provided, error'
        timezone = data.get('timezone')
        assert timezone is not None, 'Timezone is not provided, error'

        first_name = html.escape(form.get('firstName') or '')
        last_name = html.escape(form.get('lastName') or '')
        co = html.escape(form.get('company') or '')
        notes = html.escape(form.get('notes') or '')
        referral = html.escape(form.get('referral') or '')
        has_iv = html.escape(form.get('hasInterviewSoon') or '')
        exp = html.escape(form.get('experienceLevel') or '')
        qtype = html.escape(form.get('questionType') or '')

        safe_to = html.escape(to_email)
        safe_when = html.escape(f'{selected_iso} ({timezone})' if timezone else selected_iso)

        subject = f"{first_name} {last_name} | Mock Interview Confirmation"
        
        html_body = BOOKING_SUMMARY_HTML.format(
            fn=first_name,
            ln=last_name,
            safe_when=safe_when,
            safe_to=safe_to,
            has_iv=has_iv,
            co_display=co or '',
            exp_display=exp or '',
            qtype_display=qtype or '',
            notes_display=notes or '',
            referral_display=referral or '',
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        display_name = os.getenv("GMAIL_DISPLAY_NAME", "").strip()
        msg["From"] = formataddr((display_name, sender)) if display_name else sender
        msg["To"] = to_email
        msg["Bcc"] = "yiyanhuang0523@gmail.com" 
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender, password)
                server.sendmail(sender, to_email, msg.as_string())
                return jsonify({'message': 'Email sent successfully'}), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
