from dotenv import load_dotenv
from src import create_app
from flask_cors import CORS

load_dotenv()

# Khởi tạo ứng dụng Flask
app = create_app()

# Cấu hình CORS
CORS(app)

# Chạy ứng dụng ở chế độ debug và không dùng gunicorn
# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)
