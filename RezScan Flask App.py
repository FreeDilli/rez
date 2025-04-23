import logging
from Utils.logging_config import setup_logging
from flask import Flask, redirect, url_for
from config import Config
from models.database import init_db, init_app
import os

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Import blueprints
try:
    from routes.residents_export import residents_export_bp
    from routes.residents_import import residents_import_bp
    from routes.scanlog_export import scanlog_export_bp
    from routes.scanlog_delete import scanlog_delete_bp
    from routes.scanlog import scanlog_bp
    from routes.locations import locations_bp
    from routes.locations_delete import locations_delete_bp
    from routes.residents import residents_bp
    from routes.residents_edit import residents_edit_bp
    from routes.residents_delete import residents_delete_bp
    from routes.residents_delete_all import residents_delete_all_bp
    from routes.residents_import_sample import residents_sample_bp
    from routes.scan import scan_bp
    from routes.dashboard import dashboard_bp
    from routes.auth import auth_bp
    from routes.users import users_bp
    from routes.api import api_bp
    from routes.schedules import schedules_bp
    logger.info("All Blueprints imported successfully")
except ImportError as e:
    logger.error(f"ImportError: {e}")
    raise

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register blueprints
blueprints = [
    residents_export_bp, residents_import_bp, scanlog_export_bp,
    scanlog_delete_bp, scanlog_bp, locations_bp, locations_delete_bp,
    residents_bp, residents_edit_bp, residents_delete_bp,
    residents_delete_all_bp, residents_sample_bp, scan_bp,
    dashboard_bp, auth_bp, users_bp, api_bp, schedules_bp

]

for bp in blueprints:
    app.register_blueprint(bp)
    logger.info(f"Registered blueprint: {bp.name}")

init_app(app)
with app.app_context():
    init_db()

@app.route('/')
def index():
    return redirect(url_for('scan.scan'))

if __name__ == '__main__':
    logger.info("Starting Flask app")
    logger.debug(f"Registered routes: {app.url_map}")
    app.run(host='127.0.0.1', port=5080)