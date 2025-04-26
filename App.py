import logging
import os
import importlib
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, Blueprint
from flask_login import LoginManager, current_user
from utils.logging_config import setup_logging
from config import Config
from models.database import init_db, init_app, get_db
from models.User import User

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Where to redirect if not logged in

# Provide current_user to templates
@app.context_processor
def inject_current_user():
    return dict(current_user=current_user)

# Load user from user ID stored in session
@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
    return None

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Dynamic blueprint registration
def register_blueprints(app):
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
    logger.debug(f"Scanning routes directory: {routes_dir}")
    for filename in os.listdir(routes_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            logger.debug(f"Attempting to import module: routes.{module_name}")
            try:
                module = importlib.import_module(f'routes.{module_name}')
                for attr in dir(module):
                    obj = getattr(module, attr)
                    # Check if the object is a Flask blueprint
                    if isinstance(obj, Blueprint):
                        app.register_blueprint(obj)
                        logger.info(f"Registered blueprint: {obj.name}")
            except ImportError as e:
                logger.error(f"Failed to import blueprint {module_name}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing blueprint {module_name}: {e}")
                continue

# Initialize database
init_app(app)
with app.app_context():
    init_db()

# Register blueprints after app and database initialization
register_blueprints(app)
logger.info("Completed blueprint registration")

# Home route
@app.route('/')
def index():
    return redirect(url_for('scan.scan'))

# Health check route
@app.route('/health')
def health():
    try:
        db = get_db()
        db.execute('SELECT 1')  # Simple query to test SQLite connection
        logger.debug("Health check passed")
        return {'status': 'healthy'}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'unhealthy'}, 500

# Custom datetime format filter for templates
@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f').strftime('%m-%d-%Y %I:%M %p')

# Error handlers
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(504)
def gateway_timeout(e):
    return render_template("504.html"), 504

# Run the app
if __name__ == '__main__':
    logger.info("Starting Flask app")
    logger.debug(f"Registered routes: {app.url_map}")
    app.run(host='127.0.0.1', port=5080)