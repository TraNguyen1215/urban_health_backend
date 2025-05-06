import logging
import os
from flask import jsonify, request
from src.utils.db_utils import *
from . import analysis_bp

logger = logging.getLogger(__name__)

@analysis_bp.route('/nearest_facility', methods=['GET'])
def nearest_facility():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        ftype = request.args.get('type')
        ftype= ftype
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid or missing 'lat'/'lon' parameters"}), 400

    sql = """
        SELECT *,
            ST_Distance(ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, access_health.geometry::geography) AS distance_meters
        FROM public.access_health
        {where}
        ORDER BY access_health.geometry::geography <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        LIMIT 1;
    """
    where = "WHERE access_health.amenity = %s" if ftype else ""
    params = [lon, lat] + ([ftype, ftype] if ftype else []) + [lon, lat]

    try:
        conn = create_connection()
        cur = conn.cursor()
        cur.execute(sql.format(where=where), params)
        result = cur.fetchone()
        
        print(result)
        
        if not result:
            return jsonify({"message": "No facilities found"}), 404
        
        return jsonify({
            "osm_id": result[0],
            "type": result[1],
            "name": result[3],
            "healthcare_speciality": result[2],
            "distance_meters": result[-1]
        })
        
    except Exception as e:
        logger.error(f"Nearest facility error: {e}", exc_info=True)
        return jsonify({"error": "Failed to find nearest facility", "details": str(e)}), 500


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
