"""
Admin Routes for Sigmanix Chatbot
Contains all admin/analytics endpoints for dashboard access
"""

from flask import jsonify
from database import (
    get_all_students,
    get_analytics,
    calculate_student_interest,
    save_student_analysis
)


def register_admin_routes(app):
    """Register all admin routes to Flask app"""
    
    @app.get("/admin/students")
    def admin_students():
        """Get list of all students with their interest levels"""
        try:
            students = get_all_students()
            return jsonify({
                "success": True,
                "total_count": len(students),
                "students": students
            }), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.get("/admin/analytics")
    def admin_analytics():
        """Get aggregate analytics about all students"""
        try:
            analytics = get_analytics()
            return jsonify({"success": True, **analytics}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.post("/admin/recalculate/<visitor_id>")
    def admin_recalculate(visitor_id):
        """Manually recalculate student interest analysis"""
        try:
            analysis = calculate_student_interest(visitor_id)
            save_student_analysis(visitor_id, analysis)
            return jsonify({
                "success": True,
                "analysis": analysis
            }), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
