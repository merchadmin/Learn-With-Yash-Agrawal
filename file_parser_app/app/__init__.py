import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request # Added render_template, request
from pymongo import MongoClient
# Correctly import Config from instance folder
from instance.config import Config

# mongo_client = None # Removed global
# db = None # Removed global

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Load the default configuration from instance.config.Config
    app.config.from_object(Config)

    # Load override configuration from instance/config.py if it exists
    # This allows placing a config.py directly in instance/ for some settings,
    # but primary config is from the Config class loaded via from_object.
    # More commonly, environment variables override Config class defaults.
    # app.config.from_pyfile('config.py', silent=True) # Might be redundant if Config class is comprehensive

    # Ensure the instance folder exists (Flask usually handles this for instance_relative_config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Ensure the upload folder exists
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        print(f"Created upload folder at {upload_folder}")
    else:
        print(f"Upload folder already exists at {upload_folder}")

    # Initialize MongoDB client and database, storing them on the app instance
    try:
        app.mongo_client = MongoClient(app.config['MONGO_URI'], serverSelectionTimeoutMS=5000)
        app.mongo_client.admin.command('ping') # Test connection
        app.db = app.mongo_client[app.config['MONGO_DB_NAME']]
        print(f"Successfully connected to MongoDB, database '{app.config['MONGO_DB_NAME']}' is available on app.db.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        app.mongo_client = None
        app.db = None # Ensure app.db is None if connection fails

    # Register blueprints, routes, etc.
    with app.app_context():
        from . import routes # Import routes
        app.register_blueprint(routes.bp) # Register the blueprint

    # Logging Setup
    if not app.debug and not app.testing:
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)

        log_file = os.path.join(app.instance_path, 'app.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)

        formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
    else:
        # For debug/testing, use a higher level like DEBUG for console output
        app.logger.setLevel(logging.DEBUG)

    app.logger.info("Application startup")

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 Not Found: {request.path} (Referrer: {request.referrer}) - Error: {error}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 Internal Server Error: {error} at {request.path}", exc_info=True)
        return render_template('errors/500.html'), 500

    return app
