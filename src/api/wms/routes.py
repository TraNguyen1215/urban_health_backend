import os
import requests
from flask import request, Response

from . import wms_bp
from ...utils.db_utils import *

GEOSERVER_WMS_URL = os.getenv('GEOSERVER_URL') + '/nawapi/wms'


@wms_bp.route('/', methods=['GET'])
def get_wms_map():
    bbox = request.args.get('bbox')
    layer = request.args.get('layer')
    format = request.args.get('format', default='image/png')
    width = request.args.get('width', default=256, type=int)
    height = request.args.get('height', default=256, type=int)
    
    if not bbox:
        return {'error': 'bbox parameter is required'}, 400
    
    params = {
        'service': 'WMS',
        'version': '1.1.1',
        'request': 'GetMap',
        'bbox': bbox,
        'format': format,
        'srs': 'EPSG:3857',
        'transparent': 'true',
        'width': width,
        'height': height,
        'layers': layer
    }

    try:
        response = requests.get(GEOSERVER_WMS_URL, params=params, stream=True)
        
        if response.status_code == 200:
            return Response(response.content, content_type=response.headers['Content-Type'])
        else:
            return {'error': 'Failed to retrieve map from GeoServer'}, response.status_code
    except Exception as e:
        return {'error': str(e)}, 500
