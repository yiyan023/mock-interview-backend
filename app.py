import os

import stripe
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from routes.email_routes import register_email_routes
from routes.stripe_routes import register_stripe_routes
from routes.calendar_routes import register_calendar_routes

load_dotenv()

app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

_origins = os.getenv("CORS_ORIGINS")

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [o.strip() for o in _origins.split(",") if o.strip()],
        },
    },
    allow_headers=["Content-Type"],
    methods=["POST", "OPTIONS"],
)

register_stripe_routes(app)
register_email_routes(app)
register_calendar_routes(app)

@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'ok'}, 200

if __name__ == "__main__":
    app.run(port=3000, debug=True)
