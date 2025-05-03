from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
wfs_bp = Blueprint('wfs', __name__)

from . import routes