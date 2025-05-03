from flask import Flask
from dotenv import load_dotenv

def create_app():
    # Load các biến môi trường từ tệp .env
    load_dotenv()

    # Khởi tạo ứng dụng Flask
    app = Flask(__name__)

    # Đăng ký các blueprint cho các module API
    from .api.monitoring_well import monitoring_well_bp
    app.register_blueprint(monitoring_well_bp, url_prefix='/api/monitoring-well')

    from .api.monitoring_data import monitoring_data_bp
    app.register_blueprint(monitoring_data_bp, url_prefix='/api/monitoring-data')
    
    from .api.news import news_bp
    app.register_blueprint(news_bp, url_prefix='/api/news')

    from .api.layers import layers_bp
    app.register_blueprint(layers_bp, url_prefix='/api/layers')
    
    from .api.menu import menu_bp
    app.register_blueprint(menu_bp, url_prefix='/api/menu')

    from .api.wfs import wfs_bp
    app.register_blueprint(wfs_bp, url_prefix='/map/wfs')

    from .api.wms import wms_bp
    app.register_blueprint(wms_bp, url_prefix='/map/wms')


    # Trả về ứng dụng Flask đã được cấu hình
    return app
