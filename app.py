from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import tempfile
from werkzeug.utils import secure_filename
import shutil
import cv2
import numpy as np
import datetime
import requests
import re
import io
import time
import subprocess
import platform
import uuid
import random
import string
import json
import signal
import atexit

# Add path to parent directory to import toolfunny
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import toolfunny

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Đường dẫn tới file lưu trạng thái tiến trình đang chạy
ACTIVE_PROCESSES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'active_processes.json')

# Dictionary để lưu trữ các tiến trình đang hoạt động
active_processes = {}

def load_active_processes():
    """
    Tải thông tin về các tiến trình đang chạy từ file
    """
    global active_processes
    if os.path.exists(ACTIVE_PROCESSES_FILE):
        try:
            with open(ACTIVE_PROCESSES_FILE, 'r') as f:
                active_processes = json.load(f)
                print(f"Đã tải {len(active_processes)} tiến trình đang chạy từ file")
        except Exception as e:
            print(f"Lỗi khi tải tiến trình từ file: {str(e)}")
            active_processes = {}
    else:
        active_processes = {}

def save_active_processes():
    """
    Lưu thông tin về các tiến trình đang hoạt động xuống file
    """
    try:
        with open(ACTIVE_PROCESSES_FILE, 'w') as f:
            json.dump(active_processes, f, indent=2)
            print(f"Đã lưu {len(active_processes)} tiến trình xuống file")
    except Exception as e:
        print(f"Lỗi khi lưu tiến trình xuống file: {str(e)}")

def register_process(process_id, info):
    """
    Đăng ký một tiến trình mới vào danh sách đang hoạt động
    """
    active_processes[process_id] = info
    save_active_processes()

def unregister_process(process_id):
    """
    Xóa một tiến trình khỏi danh sách đang hoạt động
    """
    if process_id in active_processes:
        del active_processes[process_id]
        save_active_processes()

def cleanup_before_exit(signum=None, frame=None):
    """
    Hàm dọn dẹp trước khi thoát
    """
    print("Đang lưu trạng thái tiến trình trước khi thoát...")
    save_active_processes()

# Đăng ký hàm dọn dẹp khi thoát
atexit.register(cleanup_before_exit)
signal.signal(signal.SIGTERM, cleanup_before_exit)
signal.signal(signal.SIGINT, cleanup_before_exit)

# Tải tiến trình đang chạy khi khởi động
load_active_processes()

# Thêm route test đơn giản 
@app.route('/')
def home():
    return "Server is running! Go to /api/check-resources to test resources."

@app.route('/test')
def test():
    return jsonify({
        "status": "success",
        "message": "API test route is working"
    })

# Thêm route để kiểm tra các tiến trình đang hoạt động
@app.route('/api/active-processes')
def get_active_processes():
    return jsonify({
        "active_processes": active_processes
    })

@app.route('/check-resources')
def check_resources():
    """
    Kiểm tra các tệp tài nguyên cần thiết có sẵn hay không
    """
    try:
        resources_status = {
            'phanmengoc_folder': os.path.exists(PHANMENGOC_FOLDER),
            'funny_js': os.path.exists(os.path.join(PHANMENGOC_FOLDER, 'Funny.js')),
            'skin_folder': os.path.exists(os.path.join(PHANMENGOC_FOLDER, 'skin')),
            'plugins_folder': os.path.exists(os.path.join(PHANMENGOC_FOLDER, 'plugins')),
            'vtourskin_xml': os.path.exists(os.path.join(PHANMENGOC_FOLDER, 'skin', 'vtourskin.xml')) if os.path.exists(os.path.join(PHANMENGOC_FOLDER, 'skin')) else False,
            'output_folder': os.path.exists(OUTPUT_FOLDER)
        }
        
        # Kiểm tra tất cả các thư mục được dùng trong routes
        route_paths = {
            '/api/phanmengoc': PHANMENGOC_FOLDER,
            '/api/output': OUTPUT_FOLDER
        }
        
        missing_resources = []
        for key, exists in resources_status.items():
            if not exists:
                missing_resources.append(key)
                
        return jsonify({
            'success': len(missing_resources) == 0,
            'resources_status': resources_status,
            'missing_resources': missing_resources,
            'route_paths': {k: os.path.abspath(v) for k, v in route_paths.items()},
            'application_root': os.path.abspath(os.path.dirname(__file__))
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
WEBTOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PHANMENGOC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phanmengoc')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def extract_gdrive_folder_id(url):
    """
    Trích xuất folder ID từ đường dẫn Google Drive
    """
    # Mẫu regex cho folder ID
    pattern = r'folders/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def get_files_from_gdrive_folder(folder_id):
    """
    Lấy danh sách file từ thư mục Google Drive công khai
    Sử dụng API đơn giản không cần xác thực
    """
    try:
        # API endpoint để lấy thông tin về thư mục
        api_url = f"https://www.googleapis.com/drive/v3/files"
        params = {
            'q': f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false",
            'fields': "files(id,name,mimeType,webContentLink)",
            'key': "AIzaSyCtUn8dqqbMVeW3xo21fA-YPwJ6E-kCFcE"  
        }
        
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            return response.json().get('files', [])
        return []
    except Exception as e:
        print(f"Error fetching files from Google Drive: {str(e)}")
        return []

def is_gdown_installed():
    """
    Kiểm tra xem gdown đã được cài đặt chưa
    Returns:
        bool: True nếu gdown đã cài đặt, False nếu chưa
    """
    try:
        # Thử kiểm tra phiên bản gdown
        result = subprocess.run(['pip', 'list'], capture_output=True, text=True)
        return 'gdown' in result.stdout
    except:
        return False

def install_gdown():
    """
    Cài đặt thư viện gdown nếu cần
    Returns:
        bool: True nếu cài đặt thành công hoặc đã có sẵn, False nếu thất bại
    """
    if is_gdown_installed():
        return True
        
    print("Cài đặt gdown để tải file lớn từ Google Drive...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
        return True
    except:
        print("Không thể cài đặt gdown. Vui lòng cài thủ công: pip install gdown")
        return False

def download_with_gdown(file_id, target_path):
    """
    Tải file từ Google Drive bằng thư viện gdown
    Args:
        file_id (str): ID của file trên Google Drive
        target_path (str): Đường dẫn đầy đủ để lưu file
    Returns:
        bool: True nếu tải thành công, False nếu thất bại
    """
    if not is_gdown_installed() and not install_gdown():
        print("Không thể sử dụng gdown vì chưa được cài đặt.")
        return False
        
    print(f"Sử dụng gdown để tải file lớn (ID: {file_id})...")
    try:
        import gdown
        # Tạo thư mục chứa file nếu chưa tồn tại
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Sử dụng gdown để tải file
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, target_path, quiet=False)
        
        # Kiểm tra xem file có tồn tại và có kích thước > 0 không
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            print(f"Đã tải thành công file bằng gdown. Kích thước: {os.path.getsize(target_path)/(1024*1024):.2f} MB")
            return True
        else:
            print("Tải file bằng gdown không thành công (file trống hoặc không tồn tại)")
            return False
    except Exception as e:
        print(f"Lỗi khi sử dụng gdown: {str(e)}")
        return False

def download_file_from_gdrive(file_id, filename, target_path):
    """
    Tải file từ Google Drive theo file ID, hỗ trợ cả file lớn hơn 25MB
    Sử dụng phương pháp tải theo khối để xử lý file lớn và tiết kiệm bộ nhớ
    Sử dụng cơ chế thử lại nếu kết nối thất bại
    Sử dụng gdown làm phương án dự phòng cho file lớn
    
    Args:
        file_id (str): ID của file trên Google Drive
        filename (str): Tên file để lưu
        target_path (str): Đường dẫn đầy đủ để lưu file
        
    Returns:
        bool: True nếu tải thành công, False nếu thất bại
    """
    max_retries = 3  # Số lần thử lại tối đa
    timeout = 300  # Thời gian chờ phản hồi (5 phút)
    chunk_size = 1024 * 1024  # Kích thước khối tải: 1MB
    
    # Kiểm tra nhanh kích thước file - nếu quá lớn, dùng gdown ngay
    try:
        session = requests.Session()
        response = session.head(f"https://drive.google.com/uc?id={file_id}&export=download", timeout=30)
        
        # Nếu có header Content-Length và file > 100MB, sử dụng gdown
        if 'Content-Length' in response.headers:
            file_size = int(response.headers['Content-Length'])
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > 100:
                print(f"File lớn phát hiện ({file_size_mb:.1f} MB), sử dụng gdown để tải")
                return download_with_gdown(file_id, target_path)
    except:
        # Nếu không thể kiểm tra kích thước, tiếp tục với phương pháp thông thường
        pass
    
    # Xử lý đặc biệt cho file có tên "TONG THE NIGHT" (file lớn trong ví dụ của người dùng)
    if "TONG THE NIGHT" in filename:
        print(f"Phát hiện file đặc biệt lớn: {filename}, sử dụng gdown")
        return download_with_gdown(file_id, target_path)
    
    for retry in range(max_retries):
        try:
            # Sử dụng session để duy trì cookies
            session = requests.Session()
            
            # URL trực tiếp để tải file
            download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
            
            # Thực hiện yêu cầu ban đầu với timeout
            response = session.get(download_url, stream=True, timeout=timeout)
            
            # Kiểm tra xem có phải trang xác nhận hay không (file lớn)
            confirm_code = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_code = value
                    break
                    
            if confirm_code:
                # Thực hiện yêu cầu tải xuống với mã xác nhận
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_code}"
                print(f"File lớn phát hiện, sử dụng mã xác nhận cho {filename}")
                response = session.get(download_url, stream=True, timeout=timeout)
            
            # In thông tin về kích thước file
            if 'Content-Length' in response.headers:
                file_size = int(response.headers['Content-Length'])
                file_size_mb = file_size / (1024 * 1024)
                print(f"Đang tải {filename} từ Google Drive. Kích thước: {file_size_mb:.2f} MB")
            else:
                print(f"Đang tải {filename} từ Google Drive. Kích thước: không xác định")
            
            # Kiểm tra response
            if response.status_code == 200:
                # Nếu phản hồi có content-type là HTML và không có header Content-Disposition, có thể là trang lỗi
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type and 'Content-Disposition' not in response.headers:
                    print(f"Cảnh báo: Nhận phản hồi HTML cho {filename}. File có thể quá lớn hoặc không thể truy cập.")
                    
                    # Nếu đây là lần cuối thử với phương pháp thông thường, chuyển sang gdown
                    if retry == max_retries - 1:
                        print(f"Thử phương pháp thay thế (gdown) cho {filename}")
                        return download_with_gdown(file_id, target_path)
                    continue
                
                # Tạo thư mục chứa file nếu chưa tồn tại
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Tải file theo từng khối nhỏ để tiết kiệm bộ nhớ
                total_downloaded = 0
                start_time = time.time()
                last_update = start_time
                
                with open(target_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:  # Đảm bảo không phải chunk rỗng
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            
                            # Hiển thị tiến trình mỗi 3 giây
                            current_time = time.time()
                            if current_time - last_update > 3:
                                if 'Content-Length' in response.headers:
                                    file_size = int(response.headers['Content-Length'])
                                    progress = total_downloaded / file_size * 100
                                    elapsed = current_time - start_time
                                    speed = total_downloaded / (1024 * 1024) / elapsed if elapsed > 0 else 0
                                    print(f"Đã tải {total_downloaded/(1024*1024):.1f}MB / {file_size/(1024*1024):.1f}MB ({progress:.1f}%) - {speed:.2f} MB/s")
                                else:
                                    print(f"Đã tải {total_downloaded/(1024*1024):.1f}MB")
                                last_update = current_time
                
                print(f"Đã tải thành công {filename} vào {target_path}")
                return True
            else:
                print(f"Không thể tải file với mã trạng thái: {response.status_code}")
                # Thử lại nếu không phải lần cuối
                if retry < max_retries - 1:
                    wait_time = (retry + 1) * 5
                    print(f"Thử lại sau {wait_time} giây...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Nếu đã thử tối đa với phương pháp mặc định, chuyển sang gdown
                    print(f"Thử phương pháp thay thế (gdown) cho {filename}")
                    return download_with_gdown(file_id, target_path)
                
        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
            # Xử lý lỗi kết nối và timeout
            print(f"Lỗi kết nối khi tải {filename}: {str(e)}")
            
            if retry < max_retries - 1:
                wait_time = (retry + 1) * 5
                print(f"Thử lại sau {wait_time} giây...")
                time.sleep(wait_time)
            else:
                print(f"Không thể tải sau {max_retries} lần thử, chuyển sang gdown")
                return download_with_gdown(file_id, target_path)
                
        except Exception as e:
            print(f"Lỗi không xác định khi tải từ Google Drive: {str(e)}")
            # Nếu đây là lần cuối thử với phương pháp thông thường, chuyển sang gdown
            if retry == max_retries - 1:
                print(f"Thử phương pháp thay thế (gdown) cho {filename}")
                return download_with_gdown(file_id, target_path)
    
    # Nếu đã thử tất cả phương pháp mà vẫn thất bại
    return False

def generate_unique_project_folder(base_name):
    """
    Generate a unique project folder name by appending a random identifier
    Args:
        base_name (str): Base project name provided by user
    Returns:
        tuple: (unique_folder_name, display_name)
    """
    # Sanitize the base name to be safe for file systems
    safe_base_name = secure_filename(base_name) if base_name else "project"
    
    # Generate a random string (6 characters)
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    # Generate timestamp (YYMMDDHHmmss format)
    timestamp = datetime.datetime.now().strftime('%y%m%d%H%M%S')
    
    # Create unique folder name: sanitized_name_timestamp_random
    unique_folder_name = f"{safe_base_name}_{timestamp}_{random_id}"
    
    # Check if the folder already exists (although highly unlikely with timestamp)
    counter = 1
    test_folder = unique_folder_name
    while os.path.exists(os.path.join(OUTPUT_FOLDER, test_folder)):
        test_folder = f"{unique_folder_name}_{counter}"
        counter += 1
    
    # Return both the unique folder name and the display name
    return test_folder, base_name

@app.route('/api/fetch-from-gdrive', methods=['POST'])
def fetch_from_gdrive():
    """
    API endpoint để lấy file từ Google Drive và xử lý
    """
    try:
        data = request.get_json()
        drive_url = data.get('drive_url')
        project_name = data.get('project_name')
        
        if not drive_url:
            return jsonify({'error': 'Missing Google Drive URL'}), 400
            
        if not project_name:
            return jsonify({'error': 'Missing project name'}), 400
            
        # Trích xuất folder ID từ URL
        folder_id = extract_gdrive_folder_id(drive_url)
        if not folder_id:
            return jsonify({'error': 'Invalid Google Drive folder URL'}), 400
            
        # Tạo ID cho tiến trình này
        process_id = str(uuid.uuid4())
        
        # Generate unique folder name for this project
        unique_folder_name, display_name = generate_unique_project_folder(project_name)
        
        # Đăng ký tiến trình mới
        register_process(process_id, {
            'type': 'gdrive_fetch',
            'status': 'starting',
            'started_at': datetime.datetime.now().isoformat(),
            'project_name': project_name,
            'unique_folder': unique_folder_name,
            'folder_id': folder_id,
            'drive_url': drive_url
        })
            
        # Lấy danh sách file
        files_list = get_files_from_gdrive_folder(folder_id)
        if not files_list:
            unregister_process(process_id)
            return jsonify({'error': 'No image files found in the folder or folder is not public'}), 404
            
        # Tạo thư mục cho project
        project_upload_dir = os.path.join(UPLOAD_FOLDER, unique_folder_name)
        project_output_dir = os.path.join(OUTPUT_FOLDER, unique_folder_name)
        
        os.makedirs(project_upload_dir, exist_ok=True)
        os.makedirs(project_output_dir, exist_ok=True)
        
        # Create panosuser directory directly in project output dir
        panosuser_folder = os.path.join(project_output_dir, "panosuser")
        os.makedirs(panosuser_folder, exist_ok=True)
        
        # Cập nhật trạng thái tiến trình
        active_processes[process_id]['status'] = 'downloading'
        active_processes[process_id]['total_files'] = len(files_list)
        active_processes[process_id]['downloaded_files'] = 0
        save_active_processes()
        
        # Tải và lưu file
        downloaded_files = []
        failed_files = []
        
        print(f"Starting download of {len(files_list)} files from Google Drive")
        
        for file_info in files_list:
            file_id = file_info['id']
            filename = secure_filename(file_info['name'])
            
            # Đường dẫn đầy đủ để lưu file
            file_path = os.path.join(project_upload_dir, filename)
            
            # Cập nhật thông tin tiến trình
            active_processes[process_id]['current_file'] = filename
            save_active_processes()
            
            # Tải file trực tiếp xuống đường dẫn đích
            print(f"Downloading {filename} (ID: {file_id})")
            success = download_file_from_gdrive(file_id, filename, file_path)
            
            if success:
                downloaded_files.append(file_path)
                active_processes[process_id]['downloaded_files'] += 1
                save_active_processes()
                print(f"Successfully downloaded {filename}")
            else:
                failed_files.append(filename)
                print(f"Failed to download {filename}")
        
        if not downloaded_files:
            unregister_process(process_id)
            return jsonify({
                'error': 'Failed to download any files from Google Drive',
                'failed_files': failed_files
            }), 500
        
        # Thông báo thống kê tải xuống
        print(f"Downloaded {len(downloaded_files)} files. Failed: {len(failed_files)}")
        
        # Cập nhật trạng thái tiến trình
        active_processes[process_id]['status'] = 'processing'
        active_processes[process_id]['total_processing'] = len(downloaded_files)
        active_processes[process_id]['processed_images'] = 0
        save_active_processes()
            
        # Process files using toolfunny
        processed_images = []
        processing_failed = []
        
        for input_path in downloaded_files:
            image_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # Cập nhật thông tin tiến trình
            active_processes[process_id]['current_processing'] = image_name
            save_active_processes()
            
            # Final output path - directly in panosuser folder
            output_path = os.path.join(panosuser_folder, image_name)
            
            # Process image
            try:
                success = toolfunny.convert_spherical_to_cube_optimized(input_path, output_path, toolfunny.CUBE_SIZE)
                
                if success:
                    processed_images.append({
                        'name': image_name,
                        'input_path': input_path,
                        'output_path': output_path
                    })
                    active_processes[process_id]['processed_images'] += 1
                    save_active_processes()
                    print(f"Successfully processed {image_name}")
                else:
                    processing_failed.append(image_name)
                    print(f"Failed to process {image_name}")
            except Exception as e:
                processing_failed.append(image_name)
                print(f"Error processing {image_name}: {str(e)}")
                
        # Create XML and HTML if any images were processed successfully
        if processed_images:
            # Cập nhật trạng thái tiến trình
            active_processes[process_id]['status'] = 'finalizing'
            save_active_processes()
            
            xml_path = toolfunny.create_krpano_xml(processed_images, project_output_dir, display_name)
            html_path = toolfunny.create_krpano_html(project_output_dir, f"{display_name}")
            
            # Xóa thư mục usertools nếu nó được tạo tự động
            usertools_path = os.path.join(project_output_dir, "usertools")
            if os.path.exists(usertools_path):
                try:
                    shutil.rmtree(usertools_path)
                except Exception as e:
                    print(f"Không thể xóa thư mục {usertools_path}: {str(e)}")
            
            # Xóa thư mục uploads sau khi xử lý xong để tiết kiệm không gian
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Đã xóa thư mục uploads: {project_upload_dir}")
            except Exception as e:
                print(f"Không thể xóa thư mục uploads {project_upload_dir}: {str(e)}")
                
            # Hủy đăng ký tiến trình sau khi hoàn tất
            unregister_process(process_id)
                
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(processed_images)} images from Google Drive',
                'processed_count': len(processed_images),
                'total_count': len(files_list),
                'html_path': html_path,
                'project_name': unique_folder_name,  # Return the unique folder name
                'display_name': display_name,  # Return the original display name
                'failed_downloads': failed_files,
                'failed_processing': processing_failed
            })
        else:
            # Xóa thư mục uploads nếu không xử lý thành công
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Đã xóa thư mục uploads: {project_upload_dir}")
            except Exception as e:
                print(f"Không thể xóa thư mục uploads {project_upload_dir}: {str(e)}")
            
            # Hủy đăng ký tiến trình sau khi hoàn tất với lỗi
            unregister_process(process_id)
                
            return jsonify({
                'error': 'No images were processed successfully from Google Drive', 
                'failed_downloads': failed_files,
                'failed_processing': processing_failed
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Error processing Google Drive folder: {str(e)}'}), 500

@app.route('/api/process', methods=['POST'])
def process_images():
    """
    Endpoint to process uploaded panorama images
    """
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400

        project_name = request.form.get('projectName', 'default_project')
        files = request.files.getlist('files[]')

        if not files or len(files) == 0:
            return jsonify({'error': 'No files selected'}), 400

        # Tạo ID cho tiến trình này
        process_id = str(uuid.uuid4())

        # Generate unique folder name for this project
        unique_folder_name, display_name = generate_unique_project_folder(project_name)

        # Đăng ký tiến trình mới
        register_process(process_id, {
            'type': 'direct_upload',
            'status': 'starting',
            'started_at': datetime.datetime.now().isoformat(),
            'project_name': project_name,
            'unique_folder': unique_folder_name,
            'total_files': len(files)
        })

        # Create project directories
        project_upload_dir = os.path.join(UPLOAD_FOLDER, unique_folder_name)
        project_output_dir = os.path.join(OUTPUT_FOLDER, unique_folder_name)
        
        os.makedirs(project_upload_dir, exist_ok=True)
        os.makedirs(project_output_dir, exist_ok=True)

        # Create panosuser directory directly in project output dir
        panosuser_folder = os.path.join(project_output_dir, "panosuser")
        os.makedirs(panosuser_folder, exist_ok=True)

        # Cập nhật trạng thái tiến trình
        active_processes[process_id]['status'] = 'saving_uploads'
        save_active_processes()

        # Save uploaded files
        saved_files = []
        for i, file in enumerate(files):
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(project_upload_dir, filename)
                file.save(file_path)
                saved_files.append(file_path)
                
                # Cập nhật tiến độ
                active_processes[process_id]['current_file'] = filename
                active_processes[process_id]['uploaded_count'] = i + 1
                save_active_processes()

        if not saved_files:
            unregister_process(process_id)
            return jsonify({'error': 'Failed to save files'}), 500

        # Cập nhật trạng thái tiến trình
        active_processes[process_id]['status'] = 'processing'
        active_processes[process_id]['total_processing'] = len(saved_files)
        active_processes[process_id]['processed_count'] = 0
        save_active_processes()

        # Process files using toolfunny
        processed_images = []
        processing_failed = []
        
        for i, input_path in enumerate(saved_files):
            image_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # Cập nhật tiến độ
            active_processes[process_id]['current_processing'] = image_name
            active_processes[process_id]['processed_count'] = i
            save_active_processes()
            
            # Final output path - directly in panosuser folder
            output_path = os.path.join(panosuser_folder, image_name)
            
            # Process image
            try:
                success = toolfunny.convert_spherical_to_cube_optimized(input_path, output_path, toolfunny.CUBE_SIZE)
                
                if success:
                    processed_images.append({
                        'name': image_name,
                        'input_path': input_path,
                        'output_path': output_path
                    })
                else:
                    processing_failed.append(image_name)
            except Exception as e:
                processing_failed.append(image_name)
                print(f"Error processing {image_name}: {str(e)}")

        # Cập nhật trạng thái tiến trình
        active_processes[process_id]['status'] = 'finalizing'
        save_active_processes()

        # Create XML and HTML if any images were processed successfully
        if processed_images:
            xml_path = toolfunny.create_krpano_xml(processed_images, project_output_dir, display_name)
            html_path = toolfunny.create_krpano_html(project_output_dir, f"{display_name}")
            
            # Xóa thư mục usertools nếu nó được tạo tự động
            usertools_path = os.path.join(project_output_dir, "usertools")
            if os.path.exists(usertools_path):
                try:
                    shutil.rmtree(usertools_path)
                    print(f"Đã xóa thư mục không cần thiết: {usertools_path}")
                except Exception as e:
                    print(f"Không thể xóa thư mục {usertools_path}: {str(e)}")
            
            # Xóa thư mục uploads sau khi xử lý xong để tiết kiệm không gian
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Đã xóa thư mục uploads: {project_upload_dir}")
            except Exception as e:
                print(f"Không thể xóa thư mục uploads {project_upload_dir}: {str(e)}")
            
            # Hủy đăng ký tiến trình sau khi hoàn tất
            unregister_process(process_id)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(processed_images)} images',
                'processed_count': len(processed_images),
                'total_count': len(files),
                'html_path': html_path,
                'project_name': unique_folder_name,  # Return the unique folder name
                'display_name': display_name  # Return the original display name
            })
        else:
            # Xóa thư mục uploads nếu không xử lý thành công
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Đã xóa thư mục uploads: {project_upload_dir}")
            except Exception as e:
                print(f"Không thể xóa thư mục uploads {project_upload_dir}: {str(e)}")
                
            # Hủy đăng ký tiến trình sau khi hoàn tất với lỗi
            unregister_process(process_id)
                
            return jsonify({'error': 'No images were processed successfully'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recover-process/<process_id>', methods=['POST'])
def recover_process(process_id):
    """
    Khôi phục một tiến trình bị gián đoạn
    """
    try:
        if process_id not in active_processes:
            return jsonify({'error': 'Process not found'}), 404
            
        process_info = active_processes[process_id]
        process_type = process_info.get('type')
        
        # Kiểm tra nếu tiến trình đã hoàn tất hoặc đã lỗi
        if process_info.get('status') in ['completed', 'error']:
            return jsonify({'error': 'Process already completed or failed'}), 400
            
        # Thử khôi phục tiến trình dựa vào loại
        if process_type == 'gdrive_fetch':
            # Chuyển hướng yêu cầu tới endpoint tương ứng
            return jsonify({
                'message': 'Recovery not implemented yet. Please start a new process.',
                'process_info': process_info
            })
        elif process_type == 'direct_upload':
            return jsonify({
                'message': 'Cannot recover direct upload processes. Please start a new upload.',
                'process_info': process_info
            })
        else:
            return jsonify({'error': 'Unknown process type'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resume-unfinished', methods=['GET'])
def get_unfinished_processes():
    """
    Lấy danh sách các tiến trình chưa hoàn tất
    """
    try:
        unfinished = {pid: info for pid, info in active_processes.items() 
                     if info.get('status') not in ['completed', 'error']}
        
        return jsonify({
            'count': len(unfinished),
            'processes': unfinished
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-processes', methods=['POST'])
def clear_processes():
    """
    Xóa tất cả các tiến trình đang được theo dõi
    """
    try:
        global active_processes
        active_processes = {}
        save_active_processes()
        
        return jsonify({
            'success': True,
            'message': 'All process records cleared'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results/<path:project_name>', methods=['GET'])
def get_results(project_name):
    """
    Endpoint to get information about processed project
    """
    project_dir = os.path.join(OUTPUT_FOLDER, project_name)
    
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project not found'}), 404
    
    html_path = os.path.join(project_dir, "Toolstour.html")
    
    if os.path.exists(html_path):
        return jsonify({
            'success': True,
            'project_name': project_name,
            'html_path': html_path
        })
    else:
        return jsonify({'error': 'Project results not found'}), 404

@app.route('/api/output/<path:filename>')
def serve_output(filename):
    """
    Serve output files
    """
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/api/phanmengoc/<path:filename>')
def serve_phanmengoc(filename):
    """
    Serve phanmengoc resources
    """
    try:
        # Đầu tiên tìm trong thư mục phanmengoc nội bộ
        local_phanmengoc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phanmengoc')
        if os.path.exists(os.path.join(local_phanmengoc, filename)):
            print(f"Serving {filename} from {local_phanmengoc}")
            return send_from_directory(local_phanmengoc, filename)

        # Sau đó kiểm tra trong thư mục kho dự án
        phanmengoc_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phanmengoc")
        if os.path.exists(os.path.join(phanmengoc_folder, filename)):
            print(f"Serving {filename} from {phanmengoc_folder}")
            return send_from_directory(phanmengoc_folder, filename)
            
        # Nếu không tìm thấy ở hai nơi trên, kiểm tra WEBTOOLS_ROOT
        if os.path.exists(WEBTOOLS_ROOT):
            webtools_phanmengoc = os.path.join(WEBTOOLS_ROOT, "phanmengoc")
            if os.path.exists(os.path.join(webtools_phanmengoc, filename)):
                print(f"Serving {filename} from {webtools_phanmengoc}")
                return send_from_directory(webtools_phanmengoc, filename)
                
        # Không tìm thấy file
        print(f"File not found: {filename}")
        return f"File not found: {filename}", 404
    except Exception as e:
        print(f"Error serving {filename}: {str(e)}")
        return str(e), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """
    Lấy danh sách tất cả các dự án đã xử lý
    """
    try:
        projects = []
        for project_name in os.listdir(OUTPUT_FOLDER):
            project_dir = os.path.join(OUTPUT_FOLDER, project_name)
            
            # Chỉ xử lý thư mục
            if not os.path.isdir(project_dir):
                continue
                
            # Kiểm tra xem dự án có file HTML và XML không
            html_path = os.path.join(project_dir, "Toolstour.html")
            xml_path = os.path.join(project_dir, "user1.xml")
            
            if not (os.path.exists(html_path) and os.path.exists(xml_path)):
                continue
            
            # Extract display name from XML if possible
            display_name = project_name
            try:
                if os.path.exists(xml_path):
                    import xml.dom.minidom as minidom
                    dom = minidom.parse(xml_path)
                    krpano = dom.getElementsByTagName('krpano')
                    if krpano and krpano[0].getAttribute('title'):
                        display_name = krpano[0].getAttribute('title')
            except Exception as e:
                print(f"Error extracting display name from XML: {str(e)}")
                
            # Tìm thumbnail đầu tiên từ panosuser
            panosuser_dir = os.path.join(project_dir, "panosuser")
            thumbnail_url = None
            scene_count = 0
            
            if os.path.exists(panosuser_dir):
                # Đếm số lượng scene (thư mục con) trong panosuser
                scene_dirs = [d for d in os.listdir(panosuser_dir) if os.path.isdir(os.path.join(panosuser_dir, d))]
                scene_count = len(scene_dirs)
                
                if scene_dirs:
                    first_scene = scene_dirs[0]
                    thumb_path = os.path.join(panosuser_dir, first_scene, "thumb.jpg")
                    
                    if os.path.exists(thumb_path):
                        # Lấy đường dẫn tương đối với output folder
                        rel_path = os.path.relpath(thumb_path, OUTPUT_FOLDER)
                        thumbnail_url = f'/api/output/{rel_path}'
            
            # Thêm thông tin dự án
            projects.append({
                'name': project_name,
                'display_name': display_name,
                'html_url': f'/api/output/{project_name}/Toolstour.html',
                'thumbnail_url': thumbnail_url,
                'scene_count': scene_count,
                'created_time': os.path.getctime(project_dir)
            })
        
        # Sắp xếp theo thời gian tạo, mới nhất trước
        projects.sort(key=lambda x: x['created_time'], reverse=True)
        
        # Chuyển timestamp thành string
        for project in projects:
            project['created_time'] = datetime.datetime.fromtimestamp(project['created_time']).strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>', methods=['DELETE'])
def delete_project(project_name):
    """
    Xóa một dự án
    """
    try:
        project_dir = os.path.join(OUTPUT_FOLDER, project_name)
        
        if not os.path.exists(project_dir):
            return jsonify({'error': 'Dự án không tồn tại'}), 404
            
        # Xóa toàn bộ thư mục dự án
        shutil.rmtree(project_dir)
        
        return jsonify({
            'success': True,
            'message': f'Dự án {project_name} đã được xóa thành công'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/rename', methods=['POST'])
def rename_project(project_name):
    """
    Đổi tên dự án (chỉ đổi tên hiển thị trong XML)
    """
    try:
        data = request.get_json()
        new_name = data.get('new_name')
        
        if not new_name:
            return jsonify({'error': 'Tên mới không được để trống'}), 400
            
        # Đường dẫn tới thư mục project
        project_path = os.path.join(OUTPUT_FOLDER, project_name)
        
        # Kiểm tra xem dự án có tồn tại không
        if not os.path.exists(project_path):
            return jsonify({'error': 'Dự án không tồn tại'}), 404
            
        # Đường dẫn tới file XML
        xml_path = os.path.join(project_path, "user1.xml")
        html_path = os.path.join(project_path, "Toolstour.html")
        
        if not os.path.exists(xml_path):
            return jsonify({'error': 'File XML không tồn tại'}), 404
            
        # Cập nhật tên dự án trong file XML
        try:
            import xml.dom.minidom as minidom
            dom = minidom.parse(xml_path)
            krpano = dom.getElementsByTagName('krpano')
            if krpano:
                krpano[0].setAttribute('title', new_name)
                with open(xml_path, 'w', encoding='utf-8') as f:
                    dom.writexml(f)
                print(f"Đã cập nhật tên hiển thị trong XML thành {new_name}")
        except Exception as e:
            return jsonify({'error': f'Lỗi khi cập nhật XML: {str(e)}'}), 500
            
        # Cập nhật tên dự án trong file HTML
        if os.path.exists(html_path):
            try:
                # Đọc file HTML
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Tìm và thay thế tiêu đề
                import re
                # Thay thế trong thẻ title
                html_content = re.sub(r'<title>.*?</title>', f'<title>{new_name}</title>', html_content)
                # Thay thế trong span id="scene"
                html_content = re.sub(r'<span id="scene">.*?</span>', f'<span id="scene"> Dự Án: {new_name} </span>', html_content)
                
                # Ghi lại file HTML
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
                print(f"Đã cập nhật tên hiển thị trong HTML thành {new_name}")
            except Exception as e:
                print(f"Lỗi khi cập nhật HTML: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'Đổi tên dự án thành công thành {new_name}',
            'old_name': project_name,
            'new_name': new_name,
            'folder_name': project_name  # Tên thư mục không đổi
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-resources')
def test_resources():
    """
    Kiểm tra và hiển thị các tệp resource quan trọng
    """
    try:
        # Kiểm tra Funny.js
        funny_js_path = os.path.join(PHANMENGOC_FOLDER, 'Funny.js')
        funny_js_exists = os.path.exists(funny_js_path)
        funny_js_content = None
        if funny_js_exists:
            with open(funny_js_path, 'r', encoding='utf-8', errors='ignore') as f:
                funny_js_content = f.read(500)  # Chỉ đọc 500 ký tự đầu
        
        # Kiểm tra các dự án
        projects = []
        if os.path.exists(OUTPUT_FOLDER):
            for project_name in os.listdir(OUTPUT_FOLDER):
                project_dir = os.path.join(OUTPUT_FOLDER, project_name)
                if os.path.isdir(project_dir):
                    xml_path = os.path.join(project_dir, "user1.xml")
                    html_path = os.path.join(project_dir, "Toolstour.html")
                    xml_content = None
                    if os.path.exists(xml_path):
                        with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                            xml_content = f.read(500)  # Chỉ đọc 500 ký tự đầu
                    
                    projects.append({
                        'name': project_name,
                        'has_xml': os.path.exists(xml_path),
                        'has_html': os.path.exists(html_path),
                        'xml_sample': xml_content,
                        'html_url': f'/api/output/{project_name}/Toolstour.html',
                        'panosuser_exists': os.path.exists(os.path.join(project_dir, "panosuser"))
                    })
        
        return jsonify({
            'funny_js': {
                'exists': funny_js_exists,
                'path': funny_js_path,
                'sample': funny_js_content
            },
            'projects': projects,
            'routes': {
                'serve_phanmengoc': '/api/phanmengoc/<path:filename>',
                'serve_output': '/api/output/<path:filename>'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
