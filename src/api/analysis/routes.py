import logging
import os
from flask import jsonify, request
from src.utils.db_utils import *
from src.utils.geocoding import geocode_address
from . import analysis_bp

logger = logging.getLogger(__name__)

@analysis_bp.route('/nearest_facility_network', methods=['GET'])
def nearest_facility_network():
    try:
        address = request.args.get('address')
        if address:
            lat, lon = geocode_address(address)
            print(f"Geocoding result for '{address}': {lat}, {lon}")
            if lat is None:
                return jsonify({"error": "Không tìm được tọa độ từ địa chỉ"}), 400
            
            
        facility_type = request.args.get('type')
    except (TypeError, ValueError):
        return jsonify({"error": "Thiếu hoặc sai định dạng tham số"}), 400

    try:
        conn = create_connection()
        cur = conn.cursor()

        # 1. Tìm đỉnh gần nhất với vị trí người dùng
        cur.execute("""
            SELECT gid, source
            FROM road_vn
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1;
        """, (lon, lat))
        user_node_row = cur.fetchone()
        if not user_node_row:
            return jsonify({"error": "Không tìm thấy tuyến đường gần nhất"}), 404
        user_node = user_node_row[1]  # source

        # 2. Lấy danh sách các cơ sở y tế kèm theo node gần nhất trên graph
        where_condition = "WHERE amenity = %s" if facility_type else ""
        parameters = [facility_type] if facility_type else []

        cur.execute(f"""
            SELECT 
                access_health.id, 
                access_health.name, 
                access_health.amenity, 
                access_health.geometry,
                road_vn.source AS node_id
            FROM access_health
            JOIN road_vn
                ON ST_DWithin(access_health.geometry::geography, road_vn.geom::geography, 100)
            {where_condition};
        """, parameters)

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

        facility_node_ids = [str(f["node_id"]) for f in facilities]
        facility_node_list = ','.join(facility_node_ids)

        # 3. Tính đường đi ngắn nhất từ node của người dùng đến tất cả node cơ sở y tế
        cur.execute(f"""
            SELECT * FROM pgr_dijkstra(
                'SELECT gid, source, target, cost FROM road_vn',
                %s,
                ARRAY[{facility_node_list}],
                directed := false
            );
        """, (user_node,))

        dijkstra_rows = cur.fetchall()
        if not dijkstra_rows:
            return jsonify({"error": "Không tìm thấy tuyến đường đến cơ sở y tế nào"}), 404

        # 4. Tìm node có chi phí nhỏ nhất (gần nhất theo mạng lưới đường)
        shortest = min(dijkstra_rows, key=lambda x: x[3])  # cost
        best_node_id = shortest[2]  # node_to

        # 5. Trả lại thông tin cơ sở y tế tương ứng
        best_facility = next((f for f in facilities if f["node_id"] == best_node_id), None)
        if not best_facility:
            return jsonify({"error": "Lỗi ánh xạ cơ sở y tế"}), 500

        return jsonify({
            "osm_id": best_facility["osm_id"],
            "name": best_facility["name"],
            "type": best_facility["amenity"],
            "distance_cost": shortest[3]
        })

    except Exception as e:
        logger.error(f"Lỗi tìm kiếm cơ sở y tế theo tuyến đường: {e}", exc_info=True)
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
