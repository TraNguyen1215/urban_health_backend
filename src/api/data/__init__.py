from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
data_bp = Blueprint('data_api', __name__)

from . import routes