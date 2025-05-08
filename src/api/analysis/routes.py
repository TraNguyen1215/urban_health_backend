import logging
import os
from flask import jsonify, request
from src.utils.db_utils import *
from src.utils.geocoding import geocode_address
from . import analysis_bp

logger = logging.getLogger(__name__)

@analysis_bp.route('/nearest_facilities', methods=['GET'])
def nearest_facilities():
    conn = None
    try:
        # Nhận địa chỉ và chuyển đổi thành tọa độ
        address = request.args.get('address')
        if address:
            lat, lon = geocode_address(address)
            print(f"Geocoding result for '{address}': {lat}, {lon}")
            if lat is None:
                return jsonify({"error": "Không tìm được tọa độ từ địa chỉ"}), 400

        facility_type = request.args.get('type')
        # viết thường
        facility_type = facility_type.lower()
        
        conn = create_connection()
        cur = conn.cursor()

        # Tìm đỉnh gần nhất với vị trí người dùng
        cur.execute("""
            SELECT gid, source
            FROM road_vn
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1;
        """, (lon, lat))
        user_node_row = cur.fetchone()
        if not user_node_row:
            return jsonify({"error": "Không tìm thấy tuyến đường gần nhất"}), 404
        user_node = user_node_row[1]

        # Lấy danh sách 5 cơ sở y tế gần nhất
        cur.execute("""
            SELECT a.id, a.name, a.amenity, a.geometry, r.source AS node_id
            FROM access_health a
            JOIN LATERAL (
                SELECT source
                FROM road_vn
                ORDER BY road_vn.geom <-> a.geometry
                LIMIT 1
            ) r ON true
            WHERE a.amenity ILIKE %s
            ORDER BY a.geometry <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 5
        """, ('%' + facility_type + '%', lon, lat))

        facility_rows = cur.fetchall()
        if not facility_rows:
            return jsonify({"message": "Không tìm thấy cơ sở y tế gần"}), 404

        facilities = [
            {
                "osm_id": row[0],
                "name": row[1],
                "amenity": row[2],
                "geometry": row[3],
                "node_id": row[4]
            }
            for row in facility_rows
        ]

        return jsonify(facilities)

    except Exception as e:
        logger.error(f"Lỗi tìm kiếm cơ sở y tế gần nhất: {e}", exc_info=True)
        return jsonify({"error": "Lỗi nội bộ", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

@analysis_bp.route('/shortest_path', methods=['GET'])
def shortest_path_to_facility():
    conn = None
    try:
        # Nhận địa chỉ người dùng và cơ sở y tế
        address = request.args.get('address')
        name = request.args.get('name')
        if address and name:
            lat, lon = geocode_address(address)
            print(f"Geocoding result for '{address}': {lat}, {lon}")
            if lat is None:
                return jsonify({"error": "Không tìm được tọa độ từ địa chỉ"}), 400
        else:
            return jsonify({"error": "Thiếu tham số địa chỉ hoặc ID cơ sở y tế"}), 400

        conn = create_connection()
        cur = conn.cursor()

        # Tìm đỉnh gần nhất với vị trí người dùng
        cur.execute("""
            SELECT gid, source
            FROM road_vn
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1;
        """, (lon, lat))
        user_node_row = cur.fetchone()
        if not user_node_row:
            return jsonify({"error": "Không tìm thấy tuyến đường gần nhất"}), 404
        user_node = user_node_row[1]

        # Lấy thông tin của cơ sở y tế cần tính đường đi
        cur.execute("""
            SELECT a.id, a.name, a.amenity, r.source AS node_id
            FROM access_health a
            JOIN LATERAL (
                SELECT source
                FROM road_vn
                ORDER BY road_vn.geom <-> a.geometry
                LIMIT 1
            ) r ON true
            WHERE a.name ILIKE %s
        """, ('%' + name + '%',))
        facility_row = cur.fetchone()
        if not facility_row:
            return jsonify({"error": "Không tìm thấy cơ sở y tế với ID đã cho"}), 404

        facility = {
            "osm_id": facility_row[0],
            "name": facility_row[1],
            "amenity": facility_row[2],
            "node_id": facility_row[3]
        }

        # Tính toán đường đi ngắn nhất từ người dùng đến cơ sở y tế
        cur.execute("""
            SELECT agg_cost FROM pgr_dijkstra(
                'SELECT gid AS id, source, target, cost FROM road_vn',
                %s, %s, directed := false
            ) WHERE end_vid = %s
        """, (user_node, facility["node_id"], facility["node_id"]))
        

        result = cur.fetchall()
        if not result:
            return jsonify({"error": "Không tìm thấy tuyến đường đến cơ sở y tế"}), 404

        cost = result[-1][0]
        return jsonify({
            "osm_id": facility["osm_id"],
            "name": facility["name"],
            "type": facility["amenity"],
            "distance_cost": round(cost, 2)
        })

    except Exception as e:
        logger.error(f"Lỗi tính toán đường đi ngắn nhất: {e}", exc_info=True)
        return jsonify({"error": "Lỗi nội bộ", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@analysis_bp.route('/buffer', methods=['GET'])
def population_in_buffer():
    osm_id = request.args.get('id')
    try:
        radius = int(request.args.get('radius_meters', 1000))
        if not osm_id or radius <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Invalid 'osm_id' or 'radius_meters'"}), 400

    sql = """
        SELECT COALESCE(SUM(population_points.population_count)::bigint, 0) AS total_population
        FROM public.population_points
        JOIN public.access_health ON access_health.id = %s
        WHERE ST_DWithin(population_points.geom::geography, access_health.geometry::geography, %s)
    """

    try:
        conn = create_connection()
        cur = conn.cursor()
        cur.execute(sql, (osm_id, radius))
        row = cur.fetchone()
        
        if not row:
            return jsonify({"message": f"No population data found for facility with id {osm_id}"}), 404
        return jsonify({"osm_id": osm_id, "total_population": row[0]})
    
    except Exception as e:
        logger.error(f"Population buffer error: {e}", exc_info=True)
        return jsonify({"error": "Failed to calculate population", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@analysis_bp.route('/population_stats_by_distance', methods=['GET']) # dùng để phân tích dân số theo khoảng cách từ cơ sở y tế
def population_stats():
    ftype = request.args.get('type')
    where = "WHERE access_health.amenity = %s" if ftype else ""
    params = [ftype] if ftype else []

    sql = f"""
        WITH distances AS (
            SELECT population_points.population_count,
                (SELECT MIN(ST_Distance(population_points.geom::geography, access_health.geometry::geography))
                FROM public.access_health {where}
                ) AS min_dist
            FROM public.population_points
            WHERE population_points.population_count > 0
        )
        SELECT CASE
                WHEN min_dist <= 1000 THEN '0-1km'
                WHEN min_dist <= 3000 THEN '1-3km'
                WHEN min_dist <= 5000 THEN '3-5km'
                WHEN min_dist <= 10000 THEN '5-10km'
                ELSE '>10km'
            END AS distance_bin,
            SUM(population_count)::bigint AS total_population
        FROM distances
        WHERE min_dist IS NOT NULL
        GROUP BY distance_bin
        ORDER BY distance_bin;
    """

    try:
        conn = create_connection()
        cur = conn.cursor()
        cur.execute(sql.format(where=where), params)
        rows = cur.fetchall()
        
        print(rows)
        
        # Ensure all bins are returned even if empty
        bins = ['0-1km', '1-3km', '3-5km', '5-10km', '>10km']
        result = {r['distance_bin']: r['total_population'] for r in rows}
        return jsonify([
            {"distance_bin": b, "total_population": result.get(b, 0)} for b in bins
        ])
    except Exception as e:
        logger.error(f"Population stats error: {e}", exc_info=True)
        return jsonify({"error": "Failed to calculate stats", "details": str(e)}), 500
