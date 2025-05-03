import requests
from flask import jsonify, request
from . import wfs_bp
from ...utils.db_utils import *

GEOSERVER_WFS_URL = os.getenv('GEOSERVER_URL') + '/wfs'


@wfs_bp.route('/', methods=['GET'])
def get_wfs_layer():
    layer_name = request.args.get('layer')
    output_format = request.args.get('format', default="application/json")
    
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": layer_name,
        "outputFormat": output_format
    }
    
    try:
        response = requests.get(GEOSERVER_WFS_URL, params=params)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return {"error": "Failed to retrieve data from GeoServer"}, response.status_code
    except Exception as e:
        return {"error": str(e)}, 500
