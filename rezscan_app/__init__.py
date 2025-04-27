import os
from flask import Flask, render_template
from flask_login import LoginManager
from dotenv import load_dotenv
from rezscan_app.models.User import User

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_class=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')

    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('rezscan_app.config.Config')

    # Setup logging
    from rezscan_app.utils.logging_config import setup_logging
    setup_logging()

    login_manager.init_app(app)

    # Register Jinja2 filters
    @app.template_filter('timeformat')
    def timeformat_filter(value):
        try:
            return value.strftime('%I:%M %p') if value else ''
        except Exception:
            return value

    @app.template_filter('dateformat')
    def dateformat_filter(value):
        try:
            return value.strftime('%m/%d/%Y') if value else ''
        except Exception:
            return value

    # Initialize Database
    from rezscan_app.models.database import init_db
    with app.app_context():
        init_db()

    # Register Blueprints
    try:
        from rezscan_app.routes.auth import auth_bp
        app.register_blueprint(auth_bp)

        from rezscan_app.routes.residents import residents_bp
        app.register_blueprint(residents_bp)

        from rezscan_app.routes.scan import scan_bp
        app.register_blueprint(scan_bp)

        from rezscan_app.routes.scanlog import scanlog_bp
        app.register_blueprint(scanlog_bp)

        from rezscan_app.routes.locations import locations_bp
        app.register_blueprint(locations_bp)

        from rezscan_app.routes.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)

        from rezscan_app.routes.users import users_bp
        app.register_blueprint(users_bp)

        from rezscan_app.routes.import_history import import_history_bp
        app.register_blueprint(import_history_bp)

        from rezscan_app.routes.residents_export import residents_export_bp
        app.register_blueprint(residents_export_bp)

        from rezscan_app.routes.residents_import import residents_import_bp
        app.register_blueprint(residents_import_bp)

        from rezscan_app.routes.scanlog_export import scanlog_export_bp
        app.register_blueprint(scanlog_export_bp)

        from rezscan_app.routes.scanlog_delete import scanlog_delete_bp
        app.register_blueprint(scanlog_delete_bp)

        from rezscan_app.routes.locations_delete import locations_delete_bp
        app.register_blueprint(locations_delete_bp)

        from rezscan_app.routes.residents_edit import residents_edit_bp
        app.register_blueprint(residents_edit_bp)

        from rezscan_app.routes.residents_delete_all import residents_delete_all_bp
        app.register_blueprint(residents_delete_all_bp)

        from rezscan_app.routes.schedules import schedules_bp
        app.register_blueprint(schedules_bp)

    except Exception as e:
        print(f"Error registering blueprints: {e}")

    # ✅ Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def page_not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(504)
    def gateway_timeout_error(error):
        return render_template('504.html'), 504

    return app

# User Loader for Login Manager
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
