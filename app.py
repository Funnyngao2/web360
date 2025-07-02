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

# Add path to parent directory to import toolfunny
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import toolfunny

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
WEBTOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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

        # Create project directories
        project_upload_dir = os.path.join(UPLOAD_FOLDER, project_name)
        project_output_dir = os.path.join(OUTPUT_FOLDER, project_name)
        
        os.makedirs(project_upload_dir, exist_ok=True)
        os.makedirs(project_output_dir, exist_ok=True)

        # Create panosuser directory directly in project output dir
        panosuser_folder = os.path.join(project_output_dir, "panosuser")
        os.makedirs(panosuser_folder, exist_ok=True)

        # Save uploaded files
        saved_files = []
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(project_upload_dir, filename)
                file.save(file_path)
                saved_files.append(file_path)

        if not saved_files:
            return jsonify({'error': 'Failed to save files'}), 500

        # Process files using toolfunny
        processed_images = []
        for input_path in saved_files:
            image_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # Final output path - directly in panosuser folder
            output_path = os.path.join(panosuser_folder, image_name)
            
            # Process image
            success = toolfunny.convert_spherical_to_cube_optimized(input_path, output_path, toolfunny.CUBE_SIZE)
            
            if success:
                processed_images.append({
                    'name': image_name,
                    'input_path': input_path,
                    'output_path': output_path
                })

        # Create XML and HTML if any images were processed successfully
        if processed_images:
            xml_path = toolfunny.create_krpano_xml(processed_images, project_output_dir, project_name)
            html_path = toolfunny.create_krpano_html(project_output_dir, f"Tools Krpano {project_name}")
            
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
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(processed_images)} images',
                'processed_count': len(processed_images),
                'total_count': len(files),
                'html_path': html_path,
                'project_name': project_name
            })
        else:
            # Xóa thư mục uploads nếu không xử lý thành công
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Đã xóa thư mục uploads: {project_upload_dir}")
            except Exception as e:
                print(f"Không thể xóa thư mục uploads {project_upload_dir}: {str(e)}")
                
            return jsonify({'error': 'No images were processed successfully'}), 500

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
    phanmengoc_folder = os.path.join(WEBTOOLS_ROOT, "phanmengoc")
    return send_from_directory(phanmengoc_folder, filename)

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
                
            # Tìm thumbnail đầu tiên từ panosuser
            panosuser_dir = os.path.join(project_dir, "panosuser")
            thumbnail_url = None
            
            if os.path.exists(panosuser_dir):
                # Lấy thư mục đầu tiên trong panosuser
                scene_dirs = [d for d in os.listdir(panosuser_dir) if os.path.isdir(os.path.join(panosuser_dir, d))]
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
                'html_url': f'/api/output/{project_name}/Toolstour.html',
                'thumbnail_url': thumbnail_url,
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

@app.route('/api/projects/<path:project_name>', methods=['DELETE'])
def delete_project(project_name):
    """
    Xóa một dự án
    """
    try:
        project_dir = os.path.join(OUTPUT_FOLDER, project_name)
        
        if not os.path.exists(project_dir):
            return jsonify({'error': 'Dự án không tồn tại'}), 404
            
        # Xóa thư mục dự án
        shutil.rmtree(project_dir)
        
        return jsonify({
            'success': True,
            'message': f'Đã xóa dự án {project_name} thành công'
        })
    except Exception as e:
        return jsonify({'error': f'Không thể xóa dự án: {str(e)}'}), 500

@app.route('/api/projects/rename', methods=['POST'])
def rename_project():
    """
    Đổi tên dự án
    """
    try:
        data = request.get_json()
        
        if not data or 'old_name' not in data or 'new_name' not in data:
            return jsonify({'error': 'Thiếu thông tin cần thiết'}), 400
            
        old_name = data['old_name']
        new_name = data['new_name']
        
        # Kiểm tra tính hợp lệ của tên mới
        if not new_name or not new_name.strip():
            return jsonify({'error': 'Tên mới không hợp lệ'}), 400
            
        # Kiểm tra xem dự án cũ có tồn tại không
        old_path = os.path.join(OUTPUT_FOLDER, old_name)
        if not os.path.exists(old_path):
            return jsonify({'error': 'Dự án không tồn tại'}), 404
            
        # Kiểm tra xem tên mới đã tồn tại chưa
        new_path = os.path.join(OUTPUT_FOLDER, new_name)
        if os.path.exists(new_path):
            return jsonify({'error': 'Tên dự án mới đã tồn tại'}), 409
            
        # Đổi tên thư mục
        shutil.move(old_path, new_path)
        
        # Đường dẫn HTML mới
        new_html_url = f'/api/output/{new_name}/Toolstour.html'
        
        return jsonify({
            'success': True,
            'message': f'Đã đổi tên dự án thành công',
            'new_name': new_name,
            'html_url': new_html_url
        })
    except Exception as e:
        return jsonify({'error': f'Không thể đổi tên dự án: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 