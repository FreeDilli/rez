import os
from flask import Flask, render_template, jsonify, request
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rezscan_app.models.User import User
import importlib.util
import sys
from pathlib import Path
import logging
from datetime import datetime
from traceback import format_exc
import sqlite3
from rezscan_app.models.database import get_db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def user_key_func():
    """Return the username for authenticated users, else the remote address."""
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.url_map.strict_slashes = False
    # Setup logging first
    from rezscan_app.utils.logging_config import setup_logging
    try:
        setup_logging()
        logger = logging.getLogger('rezscan_app')  # Initialize here
        logger.info("Logging configuration initialized successfully")
        logger.debug("Starting application creation")
    except Exception as e:
        logger.error(f"Error setting up logging: {str(e)}")
        raise

    # Load configuration based on FLASK_ENV
    env = os.getenv('FLASK_ENV', 'development')
    from .config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    app.config.from_object(config_map[env])
    logger.debug(f"Loaded configuration: {config_map[env].__name__}")

    # Initialize Flask-Limiter
    try:
        limiter = Limiter(
            key_func=user_key_func,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://",  # Use redis:// for production
        )
        limiter.init_app(app)
        logger.info("Flask-Limiter initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Flask-Limiter: {str(e)}")
        raise

    # Load login manager
    try:
        login_manager.init_app(app)
        logger.info("Login manager initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing login manager: {str(e)}")
        raise

    # User Loader for Login Manager
    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = User.get(user_id)
            logger.debug(f"Loaded user: {user_id}")
            return user
        except ValueError as e:
            logger.error(f"Invalid user ID {user_id}: {str(e)}")
            return None
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error loading user {user_id}: {str(e)}\n{format_exc()}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading user {user_id}: {str(e)}\n{format_exc()}")
            return None

    # Context processor to inject user theme into all templates
    @app.context_processor
    def inject_user_theme():
        if current_user.is_authenticated:
            return {'user_theme': current_user.theme}
        return {'user_theme': 'dark'}

    # Register Jinja2 filters
    @app.template_filter('datetimeformat')
    def datetimeformat(value):
        """
        Format a datetime string from '%Y-%m-%d %H:%M:%S' to '%m-%d-%Y %H:%M:%S'.

        Args:
            value: A string in the format 'YYYY-MM-DD HH:MM:SS'.

        Returns:
            A formatted string in the format 'MM-DD-YYYY HH:MM AM/PM'.
        """
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%m-%d-%Y %H:%M:%S')
        except ValueError as e:
            logger.error(f"Failed to parse datetime '{value}': {e}")
            return value

    @app.template_filter('timeformat')
    def timeformat(value):
        """
        Format a datetime string from '%Y-%m-%d %H:%M:%S' to '%H:%M:%S'.

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
            # Create index on scans(mdoc, timestamp) for performance
            with get_db() as conn:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_mdoc_timestamp ON scans(mdoc, timestamp);")
                conn.commit()
            logger.info("Database initialized successfully with scans index")
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
        
        def scan_directory(directory):
            for item in directory.rglob('*.py'):
                if item.name.startswith('__'):
                    logger.debug(f"Skipping special file: {item.name}")
                    continue
                    
                # Convert the file path to a module path
                relative_path = item.relative_to(blueprints_dir.parent)
                module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
                module_name = f"rezscan_app.{'.'.join(module_parts)}"
                
                try:
                    logger.debug(f"Attempting to load module: {module_name}")
                    # Import the module dynamically
                    spec = importlib.util.spec_from_file_location(module_name, item)
                    if spec is None:
                        logger.error(f"Failed to create spec for module: {module_name}")
                        continue
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    # Look for blueprint instance in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, '__class__') and attr.__class__.__name__ == 'Blueprint':
                            app.register_blueprint(attr)
                            logger.info(f"Successfully registered blueprint: {attr_name} from {module_name}")
                            
                except Exception as e:
                    logger.error(f"Error registering blueprint from {module_name}: {str(e)}")

        try:
            scan_directory(blueprints_dir)
            logger.info("Blueprint registration completed")
        except Exception as e:
            logger.error(f"Error during blueprint registration: {str(e)}")

    try:
        logger.debug("Starting blueprint registration process")
        register_blueprints(app)
        logger.info("Blueprint registration completed")
    except Exception as e:
        logger.error(f"Error during blueprint registration: {str(e)}")

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f"403 Forbidden error occurred: {str(error)}, URL: {request.url}, Method: {request.method}")
        return render_template('common/403.html'), 403

    @app.errorhandler(404)
    def page_not_found_error(error):
        logger.warning(f"404 Not Found error occurred: {error}, URL: {request.url}, Method: {request.method}, Referrer: {request.referrer}")
        return render_template('common/404.html'), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        logger.warning(f"429 Rate Limit Exceeded: {str(error)}, URL: {request.url}")
        return render_template('common/429.html'), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"500 Internal Server error occurred: {str(error)}, URL: {request.url}")
        return render_template('common/500.html'), 500
    
    @app.errorhandler(504)
    def gateway_timeout_error(error):
        logger.error(f"504 Gateway Timeout error occurred: {str(error)}")
        return render_template('common/504.html'), 504

    @app.errorhandler(Exception)
    def handle_error(error):
        logger.error(f"Unhandled error: {str(error)}\n{format_exc()}")
        error_message = "An unexpected error occurred" if not app.config['DEBUG'] else str(error)
        return render_template('common/error.html', error=error_message), 500
    
    # Register is_training_mode globally for Jinja
    from rezscan_app.utils.settings import is_training_mode
    app.jinja_env.globals['is_training_mode'] = is_training_mode
    logger.debug("Registered is_training_mode as a Jinja global")

    logger.info("Application creation completed successfully")
    return app