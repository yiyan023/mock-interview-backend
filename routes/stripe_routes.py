import json
import os

import stripe
from flask import request, jsonify


def register_stripe_routes(app):
    @app.route('/api/stripe/session-status', methods=['GET'])
    def session_status():
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Stripe session ID is required'}), 400

        try:
            session = stripe.checkout.Session.retrieve(session_id)
        
        except stripe.error.InvalidRequestError:
            return jsonify({'error': 'Invalid or unknown checkout session.'}), 404
       
        except stripe.error.StripeError as e:
            print(
                f'[Stripe Error] session-status failed: {e.user_message} : {e.code} :{e.http_status}'
            )
            return jsonify({'error': e.user_message, 'code': e.code}), e.http_status

        return jsonify(
            {
                'sessionId': session.id,
                'paymentStatus': session.payment_status,
                'status': session.status,
            }
        ), 200

    @app.route('/api/stripe/create-checkout-session', methods=['POST'])
    def create_checkout_session():
        data = request.get_json(silent=True) or {}
        price_id = os.getenv('STRIPE_PRICE_ID')

        if not price_id:
            return jsonify({'error': 'STRIPE_PRICE_ID is not configured on the server.'}), 500

        form = data.get('form')
        assert form is not None, 'Form data does not exists, error'

        form_json = json.dumps(form) 

        try:
            session = stripe.checkout.Session.create(
                ui_mode='embedded_page',
                mode='payment',
                redirect_on_completion='never',
                line_items=[{'price': price_id, 'quantity': 1}],
                metadata={
                    'selected_time_iso': str(data.get('selectedTimeIso', ''))[:500],
                    'timezone': str(data.get('timezone', ''))[:500],
                    'form': form_json,
                },
            )

            if not session.client_secret:
                return jsonify({'error': 'Checkout Session has no client_secret.'}), 500

            return jsonify(
                {
                    'clientSecret': session.client_secret,
                    'sessionId': session.id,
                }
            ), 200
        
        except stripe.error.StripeError as e:
            print(f'[Stripe Error] create-checkout-session failed: {e.user_message} : {e.code} :{e.http_status}')
            return jsonify({'error': e.user_message, 'code': e.code}), e.http_status

