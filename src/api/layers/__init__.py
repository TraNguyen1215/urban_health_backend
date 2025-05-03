from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
layers_bp = Blueprint('layers', __name__)

from . import routes