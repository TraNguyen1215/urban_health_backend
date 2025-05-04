import logging
from flask import jsonify, request
from . import data_bp

from src.utils.db_utils import execute_query, parse_geojson_string

logger = logging.getLogger(__name__)


# API Phân tích: Tìm cơ sở y tế gần nhất (có thể lọc theo loại)
# @data_bp.route('/facilities', methods=['GET'])
# def get_facilities_data():
#     try:
        