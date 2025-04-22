from flask import Flask, redirect, url_for
from config import Config
from models.database import init_db, init_app
import os

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
    print("All Blueprints imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
    raise

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.register_blueprint(residents_export_bp)
app.register_blueprint(residents_import_bp)
app.register_blueprint(scanlog_export_bp)
app.register_blueprint(scanlog_delete_bp)
app.register_blueprint(scanlog_bp)
app.register_blueprint(locations_bp)
app.register_blueprint(locations_delete_bp)
app.register_blueprint(residents_bp)
app.register_blueprint(residents_edit_bp)
app.register_blueprint(residents_delete_bp)
app.register_blueprint(residents_delete_all_bp)
app.register_blueprint(residents_sample_bp)
app.register_blueprint(scan_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
print("All Blueprints registered successfully")

init_app(app)

@app.route('/')
def index():
    return redirect(url_for('scan.scan'))

if __name__ == '__main__':
    init_db()
    print(app.url_map)  # Debug: Print all registered routes
    app.run(debug=True, host='127.0.0.1', port=5080)
