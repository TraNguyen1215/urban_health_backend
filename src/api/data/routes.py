import logging
from flask import jsonify, request
from . import data_bp

from src.utils.db_utils import *

logger = logging.getLogger(__name__)

@data_bp.route('/facilities', methods=['GET'])
def get_facilities_data():
    """
    API dữ liệu thô: Trả về các cơ sở y tế (từ bảng healthcare_facilities)
    dưới dạng GeoJSON FeatureCollection.
    Cho phép lọc theo loại cơ sở (facility_type).
    """
    facility_type = request.args.get('type') # Lọc theo loại (vd: hospital, clinic)
    # Có thể thêm lọc theo bbox nếu cần

    sql = """
        SELECT
            *
        FROM access_health
        WHERE (%(facility_type)s IS NULL OR amenity = %(facility_type)s);
    """
    params = {
        'facility_type': facility_type,
    }

    try:
        conn = create_connection()
        cur = conn.cursor()
        
        cur.execute(sql, params)
        result = cur.fetchall()
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "data": [
                {
                    "osm_id": row[0],
                    "type": row[1],
                    "name": row[3],
                    "healthcare_speciality": row[2],
                    "address": row[11],
                    "opening_hours": row[4],
                    "operator": row[5],
                    "phone": row[7],
                    "website": row[8],
                    "wheelchair": row[9],
                } for row in result
            ]
        })

    except Exception as e:
        # Lỗi DB đã được log trong execute_query, chỉ cần trả về response lỗi
        # logger.error(f"Error processing get_facilities_data request (type={facility_type}): {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch or process facility data", "details": str(e)}), 500