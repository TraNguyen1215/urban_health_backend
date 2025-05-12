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
            facility_type = "nha khoa"
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
            
# thêm mới cơ sở y tế
@data_bp.route('/facility/add', methods=['POST'])
def create_facility():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        name = data.get('name')
        if not name:
            return jsonify({"error": "Missing 'name' parameter"}), 400
        facility_type = data.get('type')
        if not facility_type:
            return jsonify({"error": "Missing 'type' parameter"}), 400
        lat = data.get('lat')
        lon = data.get('lon')
        if lat is None or lon is None:
            return jsonify({"error": "Missing 'lat' or 'lon' parameters"}), 400

        # Các trường bổ sung (optional)
        healthcare_speciality = data.get('speciality', 'chung')
        address = data.get('address')
        opening_hours = data.get('opening_hours')
        operator = data.get('operator')
        operator_type = data.get('operator_type')
        phone = data.get('phone')
        website = data.get('website')
        wheelchair = data.get('wheelchair')

        conn = create_connection()
        cur = conn.cursor()

        sql = """
            INSERT INTO access_health (id,
                name, amenity, speciality, full_address, opening_hours,
                operator, operator_type, phone, website, wheelchair, geometry
            )
            VALUES (%s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
        """

        cur.execute(sql, ('node/62357',
            name, facility_type, healthcare_speciality, address, opening_hours,
            operator, operator_type, phone, website, wheelchair,
            lon, lat
        ))

        conn.commit()
        return jsonify({"message": "Facility added successfully"}), 201

    except Exception as e:
        logger.error(f"Error adding facility: {e}", exc_info=True)
        return jsonify({"error": "Failed to add facility", "details": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# cập nhật thông tin cơ sở y tế
@data_bp.route('/facility/update', methods=['POST'])
def update_facility():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        facility_id = data.get('id')
        if not facility_id:
            return jsonify({"error": "Missing 'id' parameter"}), 400

        conn = create_connection()
        cur = conn.cursor()

        # Lấy dữ liệu hiện tại
        cur.execute("SELECT * FROM access_health WHERE id = %s", (facility_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Facility not found"}), 404

        # Lấy tên cột để khớp với giá trị
        colnames = [desc[0] for desc in cur.description]
        current_data = dict(zip(colnames, row))

        # Cập nhật chỉ những trường được gửi
        name = data.get('name', current_data['name'])
        facility_type = data.get('type', current_data['amenity'])
        healthcare_speciality = data.get('speciality') or current_data.get('speciality') or "chung"
        address = data.get('address', current_data['full_address'])
        opening_hours = data.get('opening_hours', current_data['opening_hours'])
        operator = data.get('operator', current_data['operator'])
        operator_type = data.get('operator_type', current_data['operator_type'])
        phone = data.get('phone', current_data['phone'])
        website = data.get('website', current_data['website'])
        wheelchair = data.get('wheelchair', current_data['wheelchair'])

        lat = data.get('lat')
        lon = data.get('lon')

        if lat is not None and lon is not None:
            geom_sql = "ST_SetSRID(ST_MakePoint(%s, %s), 4326)"
            geom_params = (lon, lat)
        else:
            geom_sql = "%s"
            geom_params = (current_data['geometry'],)

        sql = f"""
            UPDATE access_health
            SET name = %s,
                amenity = %s,
                speciality = %s,
                full_address = %s,
                opening_hours = %s,
                operator = %s,
                operator_type = %s,
                phone = %s,
                website = %s,
                wheelchair = %s,
                geometry = {geom_sql}
            WHERE id = %s
        """

        params = (
            name, facility_type, healthcare_speciality, address, opening_hours,
            operator, operator_type, phone, website, wheelchair,
            *geom_params,
            facility_id
        )

        cur.execute(sql, params)
        conn.commit()

        return jsonify({"message": "Facility updated successfully"})

    except Exception as e:
        logger.error(f"Error updating facility: {e}", exc_info=True)
        return jsonify({"error": "Failed to update facility", "details": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# xóa cơ sở y tế
@data_bp.route('/facility/delete/<facility_id>', methods=['DELETE'])
def delete_facility(facility_id):
    try:
        conn = create_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM access_health WHERE id = %s", (facility_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Facility not found"}), 404

        # Xóa cơ sở y tế
        cur.execute("DELETE FROM access_health WHERE id = %s", (facility_id,))
        conn.commit()

        return jsonify({"message": "Facility deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting facility: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete facility", "details": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()