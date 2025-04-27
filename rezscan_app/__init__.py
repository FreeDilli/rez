import os
from flask import Flask, render_template, jsonify
from flask_login import LoginManager
from dotenv import load_dotenv
from rezscan_app.models.User import User
import importlib.util
import sys
from pathlib import Path
import logging
from datetime import datetime

load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_class=None):
    logger.debug("Starting application creation")
    
    app = Flask(__name__, static_folder='static', template_folder='templates')

    try:
        if config_class:
            logger.debug(f"Loading configuration from provided config class: {config_class}")
            app.config.from_object(config_class)
        else:
            logger.debug("Loading default configuration from rezscan_app.config.Config")
            app.config.from_object('rezscan_app.config.Config')
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

    # Setup logging
    from rezscan_app.utils.logging_config import setup_logging
    try:
        setup_logging()
        logger.info("Logging configuration initialized successfully")
    except Exception as e:
        logger.error(f"Error setting up logging: {str(e)}")
        raise

    try:
        login_manager.init_app(app)
        logger.info("Login manager initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing login manager: {str(e)}")
        raise

    # Register Jinja2 filters
    @app.template_filter('datetimeformat')
    def datetimeformat(value):
        """
        Format a datetime string from '%Y-%m-%d %H:%M:%S' to '%m-%d-%Y %I:%M %p'.

        Args:
            value: A string in the format 'YYYY-MM-DD HH:MM:SS'.

        Returns:
            A formatted string in the format 'MM-DD-YYYY HH:MM AM/PM'.
        """
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%m-%d-%Y %I:%M %p')
        except ValueError as e:
            logger.error(f"Failed to parse datetime '{value}': {e}")
            return value

    @app.template_filter('timeformat')
    def timeformat(value):
        """
        Format a datetime string from '%Y-%m-%d %H:%M:%S' to '%I:%M %p'.

        Args:
            value: A string in the format 'YYYY-MM-DD HH:MM:SS'.

        Returns:
            A formatted string in the format 'HH:MM AM/PM'.
        """
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
        except ValueError as e:
            logger.error(f"Failed to parse time '{value}': {e}")
            return value
    
    @app.template_filter('dateformat')
    def dateformat(value):
        """
        Format a datetime string from '%Y-%m-%d %H:%M:%S' to '%m-%d-%Y'.

        Args:
            value: A string in the format 'YYYY-MM-DD HH:MM:SS'.

        Returns:
            A formatted string in the format 'MM-DD-YYYY'.
        """
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%m-%d-%Y')
        except ValueError as e:
            logger.error(f"Failed to parse date '{value}': {e}")
            return value

    # Initialize Database
    from rezscan_app.models.database import init_db, close_db
    with app.app_context():
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    # Register database teardown
    app.teardown_appcontext(close_db)
    logger.debug("Registered database teardown handler")

    # Health Check Endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        try:
            logger.debug("Health check requested")
            return jsonify({"status": "healthy", "message": "Application is running"}), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({"status": "unhealthy", "message": str(e)}), 500

    # Dynamic Blueprint Registration
    def register_blueprints(app):
        blueprints_dir = Path(__file__).parent / 'routes'
        logger.debug(f"Scanning blueprints directory: {blueprints_dir}")
        
        for module_path in blueprints_dir.glob('*.py'):
            if module_path.name.startswith('__'):
                logger.debug(f"Skipping special file: {module_path.name}")
                continue
                
            module_name = f"rezscan_app.routes.{module_path.stem}"
            try:
                logger.debug(f"Attempting to load module: {module_name}")
                # Import the module dynamically
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Look for blueprint instance in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, '__class__') and attr.__class__.__name__ == 'Blueprint':
                        app.register_blueprint(attr)
                        logger.info(f"Successfully registered blueprint: {attr_name}")
                        
            except Exception as e:
                logger.error(f"Error registering blueprint from {module_name}: {str(e)}")

    try:
        logger.debug("Starting blueprint registration process")
        register_blueprints(app)
        logger.info("Blueprint registration completed")
    except Exception as e:
        logger.error(f"Error during blueprint registration: {str(e)}")

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f"403 Forbidden error occurred: {str(error)}")
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def page_not_found_error(error):
        logger.warning(f"404 Not Found error occurred: {str(error)}")
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"500 Internal Server error occurred: {str(error)}")
        return render_template('500.html'), 500

    logger.info("Application creation completed successfully")
    return app

# User Loader for Login Manager
@login_manager.user_loader
def load_user(user_id):
    try:
        user = User.get(user_id)
        logger.debug(f"Loaded user: {user_id}")
        return user
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        return None