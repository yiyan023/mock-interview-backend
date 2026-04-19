import os
import uuid
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import jsonify, request


def get_calendar_service():
    """Build an authenticated Google Calendar API client using stored refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    return build("calendar", "v3", credentials=creds)


def register_calendar_routes(app):
    @app.route('/api/calendar/create-event', methods=['POST'])
    def create_calendar_event():
        data = request.get_json(silent=True)
        assert data is not None, 'Data does not exists, error'
        form = data.get('form')
        assert form is not None, 'Form data does not exists, error'

        selected_iso = data.get('selectedTimeIso')
        assert selected_iso is not None, 'Selected time ISO is not provided, error'
        timezone = data.get('timezone')
        assert timezone is not None, 'Timezone is not provided, error'

        to_email = form.get('email').strip()
        assert to_email is not None, 'Email is not provided, error'
        
        first_name = form.get('firstName').strip()
        assert first_name is not None, 'First name is not provided, error'
        
        last_name = form.get('lastName').strip()
        assert last_name is not None, 'Last name is not provided, error'
        
        notes = form.get('notes').strip()
        assert notes is not None, 'Notes is not provided, error'

        try:
            start_dt = datetime.fromisoformat(selected_iso.replace('Z', '+00:00'))
            end_dt = start_dt + timedelta(hours=1)
        
        except ValueError:
            return jsonify({'error': 'Invalid time format'}), 400

        event = {
            'summary': f'Mock Interview with Yiyan | {first_name} {last_name}',
            'description': f'Hey {first_name}! Thanks for scheduling a mock interview with me. Please email me if you would like to cancel or reschedule.',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': timezone,
            },
            'attendees': [
                {'email': to_email},
                {'email': 'yiyanhuang0523@gmail.com'},
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                },
            },
            'reminders': {
                'useDefault': True,
            },
        }

        try:
            service = get_calendar_service()
            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all',
            ).execute()

            return jsonify({
                'message': 'Event created successfully',
                'meetLink': created_event.get('hangoutLink'),
                'eventLink': created_event.get('htmlLink'),
                'eventId': created_event.get('id'),
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500