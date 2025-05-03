from flask import Flask, Blueprint
import os
import sys
from pathlib import Path
import importlib
import csv

# Add project root to Python path to resolve imports like 'rezscan_app'
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Create Flask app
app = Flask(__name__)

# Main app routes (example routes; replace with your actual routes)
@app.route('/')
def home():
    return 'Home'

@app.route('/about')
def about():
    return 'About'

# Dynamically import and register blueprints from rezscan_app/routes directory and subdirectories
def register_blueprints(app):
    routes_dir = os.path.join(os.path.dirname(__file__), 'rezscan_app', 'routes')
    if not os.path.exists(routes_dir):
        print("No routes directory found at rezscan_app/routes/. Skipping blueprint registration.")
        return
    
    for root, _, files in os.walk(routes_dir):
        for filename in files:
            if filename.endswith('.py') and filename != '__init__.py':
                # Convert file path to module name (e.g., rezscan_app.routes.admin.audit_log)
                rel_path = os.path.relpath(os.path.join(root, filename[:-3]), os.path.dirname(__file__))
                module_name = rel_path.replace(os.sep, '.')  # Replace path separators with dots
                try:
                    module = importlib.import_module(module_name)
                    # Find all Blueprint instances in the module
                    blueprints = [obj for obj in module.__dict__.values() if isinstance(obj, Blueprint)]
                    for bp in blueprints:
                        app.register_blueprint(bp)
                        print(f"Registered blueprint: {bp.name} from {module_name}")
                except ImportError as e:
                    print(f"Failed to import {module_name}: {e}")

# Function to get all routes, including from all registered blueprints
def get_all_routes(app):
    routes = []
    for rule in app.url_map.iter_rules():
        # Filter out HEAD and OPTIONS for clarity
        methods = ','.join(sorted(m for m in rule.methods if m not in ['HEAD', 'OPTIONS']))
        # Determine if the route belongs to a blueprint or the main app
        blueprint = rule.endpoint.split('.')[0] if '.' in rule.endpoint else None
        routes.append({
            'blueprint': blueprint or 'app',
            'url': rule.rule,
            'endpoint': rule.endpoint,
            'methods': methods
        })
    # Sort by blueprint and URL for readability
    return sorted(routes, key=lambda x: (x['blueprint'], x['url']))

# Export routes to CSV
def export_routes_to_csv(routes, filename='routes_export.csv'):
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['blueprint', 'url', 'endpoint', 'methods'])
            writer.writeheader()
            for route in routes:
                writer.writerow(route)
        print(f"Routes exported to {filename}")
    except Exception as e:
        print(f"Failed to export routes to CSV: {e}")

# Register blueprints and print/export routes
if __name__ == '__main__':
    # Register all blueprints dynamically
    register_blueprints(app)
    
    # Get all routes
    routes = get_all_routes(app)
    
    # Print all routes
    print("\nAll Routes in the Flask App:")
    print("-" * 50)
    for route in routes:
        print(f"Blueprint: {route['blueprint']:<20} URL: {route['url']:<40} Endpoint: {route['endpoint']:<30} Methods: {route['methods']}")
    
    # Export routes to CSV
    export_routes_to_csv(routes)
    
    # Optionally, run the app (uncomment to start server)
    # app.run(debug=True)