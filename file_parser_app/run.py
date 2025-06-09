from app import create_app
import os

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    # Use PORT environment variable if available (e.g. for Heroku), otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Set debug=True for development, it's good to get this from an env var too
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
