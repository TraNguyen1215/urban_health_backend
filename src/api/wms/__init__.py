from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
wms_bp = Blueprint('wms', __name__)

from . import routes