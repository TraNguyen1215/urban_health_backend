from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
data_bp = Blueprint('data', __name__)

from . import routes