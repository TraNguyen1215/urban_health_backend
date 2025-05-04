import logging
from flask import Blueprint, jsonify, request

from src.utils.db_utils import *
from . import analysis_bp

logger = logging.getLogger(__name__)

@analysis_bp.route('/nearest_facility', methods=['GET'])
def get_nearest_facility_analysis():
    """
    API Phân tích: Tìm cơ sở y tế gần nhất (có thể lọc theo loại amenity/speciality)
    với lat/lon cho trước.
    Trả về thông tin về cơ sở gần nhất và khoảng cách.
    Sử dụng bảng public.access_health.
    """
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        # Sử dụng tham số 'type' để lọc theo amenity HOẶC healthcare_speciality
        facility_type_filter = request.args.get('type', None)

    except (TypeError, ValueError, AttributeError):
        logger.warning(f"Invalid nearest_facility analysis parameters: {request.args}")
        return jsonify({"error": "Invalid or missing 'lat'/'lon' query parameters."}), 400

    # Xây dựng phần WHERE clause dựa trên tham số 'type'
    where_clause = ""
    params = [lon, lat] # Base parameters for ST_MakePoint
    if facility_type_filter:
        # Lọc theo amenity HOẶC healthcare_speciality
        where_clause = " WHERE (f.amenity = %(type)s)"
        params.append(facility_type_filter) # Add type parameter
        # Append lon, lat again for ORDER BY if type filter is used
        params.extend([lon, lat])
    else:
        # Append lon, lat for ORDER BY if no type filter
        params.extend([lon, lat])


    # Query tìm cơ sở gần nhất, có thể lọc theo loại
    sql = f"""
        SELECT
            f.osm_id,
            f.name,
            f.amenity,
            f.healthcare_speciality,
            ST_Distance(
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                f.geometry::geography -- Sử dụng cột 'geometry'
            ) as distance_meters
            
        FROM public.access_health f
        {where_clause} -- Chèn mệnh đề WHERE (có thể trống)
        ORDER BY f.geometry::geography <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        LIMIT 1;
    """
    # Chuyển danh sách params thành tuple
    params = tuple(params)


    try:
        conn = create_connection()
        cur = conn.cursor()
        result = cur.execute(sql, params)
        
        if result:
            nearest = {
                "osm_id": result.get('id'),
                "name": result.get('name'),
                "amenity": result.get('amenity'),
                "healthcare_speciality": result.get('healthcare_speciality'),
                "distance_meters": round(result.get('distance_meters', 0), 2),
            }
            return jsonify(nearest)
        else:
            # Thông báo không tìm thấy dựa trên loại nếu có lọc
            message = f"No healthcare facility found near ({lat},{lon})"
            if facility_type_filter:
                message = f"No facility of type '{facility_type_filter}' found near ({lat},{lon})"
            logger.info(message)
            return jsonify({"message": message}), 404

    except Exception as e:
        logger.error(f"Error finding nearest facility for ({lat},{lon}, type={facility_type_filter}): {e}", exc_info=True)
        return jsonify({"error": "Failed to find nearest facility", "details": str(e)}), 500

@analysis_bp.route('/population_in_buffer', methods=['GET'])
def get_population_in_buffer_analysis():
    """
    API Phân tích: Tính dân số ước tính trong bán kính (mét)
    quanh một cơ sở y tế cụ thể (dùng osm_id).
    Trả về tổng dân số.
    Sử dụng bảng public.access_health và public.population_points.
    """
    # Lấy osm_id của cơ sở y tế
    facility_osm_id = request.args.get('id')
    radius_meters_str = request.args.get('radius_meters', '1000') 

    if not facility_osm_id:
        logger.warning("Missing osm_id for population_in_buffer analysis.")
        return jsonify({"error": "Parameter 'osm_id' is required"}), 400

    try:
        radius_meters = int(radius_meters_str)
        if radius_meters <= 0:
            return jsonify({"error": "Radius must be positive"}), 400
    except ValueError:
        logger.warning(f"Invalid radius for population_in_buffer analysis: {radius_meters_str}")
        return jsonify({"error": "Invalid radius value"}), 400

    # Query tính tổng dân số trong buffer
    sql = """
        SELECT COALESCE(SUM(pp.population_count)::bigint, 0) AS total_population
        FROM public.population_points
        JOIN public.access_health ON access_health.id = %s -- Sử dụng tên bảng và cột osm_id đúng
        WHERE ST_DWithin(population_points.geometry::geography, access_health.geometry::geography, %s);
    """
    params = (facility_osm_id, radius_meters)

    try:
        conn = create_connection()
        cur = conn.cursor()
        result = cur.execute(sql, params)
        population_count = int(result.get('total_population', 0)) if result else 0

        return jsonify({
            "facility_osm_id": facility_osm_id,
            "radius_meters": radius_meters,
            "estimated_population": population_count
        })

    except Exception as e:
        logger.error(f"Error calculating population in buffer for facility {facility_osm_id} with radius {radius_meters}: {e}", exc_info=True)
        return jsonify({"error": "Failed to calculate population in buffer", "details": str(e)}), 500


@analysis_bp.route('/population_stats_by_distance', methods=['GET'])
def get_population_stats_by_distance_analysis():
    """
    API Phân tích: Tính toán phân bố dân số theo khoảng cách tới cơ sở y tế GẦN NHẤT.
    Trả về dữ liệu thống kê cho biểu đồ.
    Sử dụng bảng public.access_health và public.population_points.
    """
    # Có thể thêm tham số lọc theo loại cơ sở y tế amenity/speciality nếu muốn thống kê khoảng cách đến loại cụ thể
    facility_type_filter = request.args.get('type', None)

    # Xây dựng phần WHERE clause cho subquery nếu có lọc theo loại
    subquery_where_clause = ""
    params = []
    if facility_type_filter:
        # Lọc theo amenity HOẶC healthcare_speciality trong subquery
        subquery_where_clause = " WHERE (f.amenity = %s)"
        params.extend([facility_type_filter, facility_type_filter])

    # Query thống kê dân số theo khoảng cách tới cơ sở y tế GẦN NHẤT (có thể lọc theo loại)
    sql = f"""
        WITH PointDistances AS (
            SELECT
                pp.population_count,
                (SELECT MIN(ST_Distance(pp.geometry::geography, f.geometry::geography)
                    FROM public.access_health f 
                    {subquery_where_clause} 
                    -- ORDER BY pp.geometry::geography <-> f.geometry::geography -- Tối ưu nếu cần và đã thêm tham số
                    -- LIMIT 1
                ) as min_distance_meters
            FROM public.population_points pp
            WHERE pp.population_count > 0 AND pp.geometry
        )
        SELECT
            CASE
                WHEN min_distance_meters <= 1000 THEN '0-1km'
                WHEN min_distance_meters > 1000 AND min_distance_meters <= 3000 THEN '1-3km'
                WHEN min_distance_meters > 3000 AND min_distance_meters <= 5000 THEN '3-5km'
                WHEN min_distance_meters > 5000 AND min_distance_meters <= 10000 THEN '5-10km'
                ELSE '>10km'
            END as distance_bin,
            SUM(population_count)::bigint as total_population
        FROM PointDistances
        WHERE min_distance_meters IS NOT NULL
        GROUP BY distance_bin
        ORDER BY
            CASE distance_bin
                WHEN '0-1km' THEN 1 WHEN '1-3km' THEN 2 WHEN '3-5km' THEN 3
                WHEN '5-10km' THEN 4 ELSE 5
            END;
    """
    # Chuyển danh sách params thành tuple (chỉ chứa tham số lọc loại nếu có)
    params = tuple(params)

    try:
        conn = create_connection()
        cur = conn.cursor()
        stats_result = cur.execute(sql, params)
        if stats_result is None:
            raise Exception("Failed to retrieve distance statistics from database.")

        all_bins = ['0-1km', '1-3km', '3-5km', '5-10km', '>10km']
        stats_dict = {item['distance_bin']: int(item['total_population']) for item in stats_result}
        formatted_stats = [{"distance_bin": bin_name, "total_population": stats_dict.get(bin_name, 0)} for bin_name in all_bins]

        return jsonify(formatted_stats)

    except Exception as e:
        logger.error(f"Error calculating population stats by distance (type={facility_type_filter}): {e}", exc_info=True)
        return jsonify({"error": "Failed to calculate population statistics", "details": str(e)}), 500