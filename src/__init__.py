from flask import Flask
from dotenv import load_dotenv

def create_app():
     # Load các biến môi trường từ tệp .env
     load_dotenv()

     # Khởi tạo ứng dụng Flask
     app = Flask(__name__)

     # Đăng ký các blueprint cho các module API

     from .api.analysis import analysis_bp
     app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
     
     from .api.data import data_bp
     app.register_blueprint(data_bp, url_prefix='/api/data')

     from .api.wfs import wfs_bp
     app.register_blueprint(wfs_bp, url_prefix='/map/wfs')

     from .api.wms import wms_bp
     app.register_blueprint(wms_bp, url_prefix='/map/wms')


     # Trả về ứng dụng Flask đã được cấu hình
     return app
