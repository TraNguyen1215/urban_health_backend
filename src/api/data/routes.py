import logging
from flask import jsonify, request
from . import data_bp

from src.utils.db_utils import *

logger = logging.getLogger(__name__)

# lấy tất cả các cơ sở y tế từ DB
@data_bp.route('/facilities', methods=['GET'])
def get_facilities_data():
    try:
        conn = create_connection()
        cur = conn.cursor()
        
        sql = """SELECT * FROM access_health"""
        
        cur.execute(sql)
        result = cur.fetchall()
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "data": [
                {
                    "osm_id": row[0],
                    "type": row[1],
                    "name": row[3],
                    "healthcare_speciality": row[2] if row[2] else "chung",
                    "address": row[11],
                    "opening_hours": row[4],
                    "operator": row[5],
                    "operator_type": row[6],
                    "phone": row[7],
                    "website": row[8],
                    "wheelchair": row[9],
                } for row in result
            ]
        })

    except Exception as e:
        return jsonify({"error": "Failed to fetch or process facility data", "details": str(e)}), 500
    
    finally:
        if conn:
            conn.close()
            
# lấy theo loại cơ sở y tế
@data_bp.route('/facilities/<facility_type>', methods=['GET'])
def get_facility_by_type(facility_type):
    try:
        if(not facility_type):
            return jsonify({"error": "Invalid or missing 'facility_type' parameter"}), 400
        elif(facility_type == "hospital"):
            facility_type = "bệnh viện"
        elif(facility_type == "pharmacy"):
            facility_type = "nhà thuốc"
        elif(facility_type == "doctor"):
            facility_type = "phòng khám tư nhân"
        elif(facility_type == "clinic"):
            facility_type = "trạm y tế/phòng khám"
        elif(facility_type == "dentist"):
            facility_type = "phòng khám nha khoa"
        elif(facility_type == "alternative"):
            facility_type = "y học cổ truyền"
        elif(facility_type == "blood_donation"):
            facility_type = "trung tâm hiến máu"
        elif(facility_type == "vacxin"):
            facility_type = "trung tâm tiêm vacxin"
        
        conn = create_connection()
        cur = conn.cursor()
        
        sql = """SELECT * FROM access_health WHERE amenity = %s"""
        
        cur.execute(sql, (facility_type,))
        result = cur.fetchall()
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "data": [
                {
                    "osm_id": row[0],
                    "type": row[1],
                    "name": row[3],
                    "healthcare_speciality": row[2] if row[2] else 'chung',
                    "address": row[11],
                    "opening_hours": row[4],
                    "operator": row[5],
                    "operator_type": row[6],
                    "phone": row[7],
                    "website": row[8],
                    "wheelchair": row[9],
                } for row in result
            ]
        })

    except Exception as e:
        return jsonify({"error": "Failed to fetch or process facility data", "details": str(e)}), 500
    
    finally:
        if conn:
            conn.close()

# tìm cơ sở y tế theo tên
@data_bp.route('/facilities/search', methods=['GET'])
def search_facility_by_name():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Invalid or missing 'name' parameter"}), 400

    try:
        conn = create_connection()
        cur = conn.cursor()
        
        sql = """SELECT * FROM access_health WHERE name ILIKE %s"""
        
        cur.execute(sql, ('%' + name + '%',))
        result = cur.fetchall()
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "data": [
                {
                    "osm_id": row[0],
                    "type": row[1],
                    "name": row[3],
                    "healthcare_speciality": row[2] if row[2] else 'chung',
                    "address": row[11],
                    "opening_hours": row[4],
                    "operator": row[5],
                    "operator_type": row[6],
                    "phone": row[7],
                    "website": row[8],
                    "wheelchair": row[9],
                } for row in result
            ]
        })

    except Exception as e:
        return jsonify({"error": "Failed to fetch or process facility data", "details": str(e)}), 500
    
    finally:
        if conn:
            conn.close()
            
# lấy riêng một cơ sở y tế theo id
@data_bp.route('/facility', methods=['GET'])
def get_facility_by_id():
    try:
        facility_id = request.args.get('id')
        conn = create_connection()
        cur = conn.cursor()
        
        sql = """SELECT * FROM access_health WHERE id = %s"""
        
        cur.execute(sql, (facility_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "osm_id": result[0],
            "type": result[1],
            "name": result[3],
            "healthcare_speciality": result[2] if result[2] else 'chung',
            "address": result[11],
            "opening_hours": result[4],
            "operator": result[5],
            "operator_type": result[6],
            "phone": result[7],
            "website": result[8],
            "wheelchair": result[9],
        })

    except Exception as e:
        return jsonify({"error": "Failed to fetch or process facility data", "details": str(e)}), 500
    
    finally:
        if conn:
            conn.close()

# lấy mật độ dân số theo cơ sở y tế
@data_bp.route('/facilities/density', methods=['GET'])
def get_facility_density():
    try:
        conn = create_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT access_health.osm_id, access_health.name, COUNT(population_points.id) AS population_count
            FROM access_health
            LEFT JOIN population_points ON ST_DWithin(access_health.geometry, population_points.geom, 1000)
            GROUP BY access_health.osm_id, access_health.name
        """
        
        cur.execute(sql)
        result = cur.fetchall()
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "data": [
                {
                    "osm_id": row[0],
                    "name": row[1],
                    "population_count": row[2]
                } for row in result
            ]
        })

    except Exception as e:
        return jsonify({"error": "Failed to fetch or process facility data", "details": str(e)}), 500
    
    finally:
        if conn:
            conn.close()