import os
from flask import Flask, render_template, jsonify
from config import config
from database.db import init_db
from services.synthetic_data import seed_synthetic_data
from routes.views import views_bp
from routes.api_routes import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize DB and pre-seed benchmark data
    with app.app_context():
        init_db()
        seed_synthetic_data()

    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # Template context processor for global variables
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "HireLens AI",
            "tagline": "Evidence-Based Hiring Platform",
            "openai_configured": bool(config.OPENAI_API_KEY)
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("base.html", error_title="404 - Page Not Found", error_message="The requested recruitment intelligence resource could not be found."), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"success": False, "error": "Uploaded resume exceeds the maximum 16MB file limit."}), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("base.html", error_title="500 - System Error", error_message="An internal server error occurred. Check activity logs for details."), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
