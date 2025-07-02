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
from math import pi, atan2, asin
from glob import glob
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
import threading
from functools import partial
import xml.dom.minidom as minidom
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure folders based on environment
if os.environ.get("RAILWAY_ENVIRONMENT"):
    # On Railway, use the /tmp directory for uploads and output
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    OUTPUT_FOLDER = os.path.join('/tmp', 'output')
    WEBTOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Create a static folder for phanmengoc resources
    PHANMENGOC_FOLDER = os.path.join('/tmp', 'phanmengoc')
    
    # Copy phanmengoc resources to tmp folder if they exist in the app
    src_phanmengoc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phanmengoc')
    if os.path.exists(src_phanmengoc):
        if not os.path.exists(PHANMENGOC_FOLDER):
            shutil.copytree(src_phanmengoc, PHANMENGOC_FOLDER)
else:
    # Local development
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    WEBTOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PHANMENGOC_FOLDER = os.path.join(WEBTOOLS_ROOT, "phanmengoc")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Constants moved from toolfunny.py
CUBE_SIZE = 1920
MAX_WORKERS = min(cpu_count(), 8)  # Limit workers to prevent memory overload

# Image processing functions from toolfunny.py
face_params = {
    'pano_f': lambda x, y, z: ( x,  y,  z),    # front
    'pano_r': lambda x, y, z: ( z,  y, -x),    # right
    'pano_b': lambda x, y, z: (-x,  y, -z),    # back
    'pano_l': lambda x, y, z: (-z,  y,  x),    # left
    'pano_d': lambda x, y, z: ( x,  z, -y),    # up
    'pano_u': lambda x, y, z: ( x, -z,  y),    # down
}

def resize_panorama_fast(image, target_width=6144, target_height=3072):
    """
    Resize panorama with higher ratio to improve quality
    """
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)

def vector_to_spherical(x, y, z):
    theta = atan2(x, z)  # longitude
    phi = asin(y)        # latitude
    return theta, phi

def create_cube_face_optimized(pano_img, face, size):
    """
    Optimize cube face creation using numpy vectorization
    """
    h, w = pano_img.shape[:2]
    
    # Create grid coordinates once
    y_coords, x_coords = np.mgrid[0:size, 0:size]
    
    # Normalize coordinates
    nx = (2 * x_coords / size) - 1
    ny = (2 * y_coords / size) - 1
    
    # Calculate vectors
    length = np.sqrt(nx*nx + ny*ny + 1)
    
    # Apply face transformation
    face_func = face_params[face]
    vx, vy, vz = face_func(nx, ny, np.ones_like(nx))
    
    # Normalize vectors
    vx = vx / length
    vy = vy / length
    vz = vz / length
    
    # Convert to spherical coordinates
    theta = np.arctan2(vx, vz)
    phi = np.arcsin(vy)
    
    # Convert to image coordinates
    uf = 0.5 * (theta / pi + 1)
    vf = 0.5 * (phi / (pi/2) + 1)
    
    px = (uf * (w - 1)).astype(np.int32)
    py = ((1 - vf) * (h - 1)).astype(np.int32)
    
    # Clamp coordinates
    px = np.clip(px, 0, w-1)
    py = np.clip(py, 0, h-1)
    
    # Sample from panorama
    face_img = pano_img[py, px]
    
    return face_img

def create_cube_face_batch(args):
    """
    Wrapper function for multiprocessing
    """
    pano_img, face, size = args
    return face, create_cube_face_optimized(pano_img, face, size)

def rotate_image(img, angle):
    if angle == 0:
        return img
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h))
    return rotated

def correct_rotation(face, img):
    rotation_angles = {
        'pano_f': 0,
        'pano_l': 0,
        'pano_r': 0,
        'pano_u': 0,
        'pano_d': 0,
        'pano_b': 0
    }
    angle = rotation_angles.get(face, 0)
    return rotate_image(img, angle)

def create_preview_image_fast(faces_dict, output_folder, preview_size=(256, 1536)):
    """
    Create preview faster with threading and higher quality
    """
    width, height = preview_size
    face_height = height // 6
    face_width = width

    preview_img = np.zeros((height, width, 3), dtype=np.uint8)
    order = ['pano_r', 'pano_f', 'pano_l', 'pano_b', 'pano_u', 'pano_d']

    def resize_face(i, face):
        img = faces_dict.get(face)
        if img is not None:
            resized = cv2.resize(img, (face_width, face_height), interpolation=cv2.INTER_LANCZOS4)
            preview_img[i*face_height:(i+1)*face_height, 0:face_width] = resized

    # Use threading for parallel resize
    threads = []
    for i, face in enumerate(order):
        thread = threading.Thread(target=resize_face, args=(i, face))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    preview_path = os.path.join(output_folder, "preview.jpg")
    cv2.imwrite(preview_path, preview_img, [cv2.IMWRITE_JPEG_QUALITY, 100])
    return preview_path

def create_thumbnail_fast(face_img, output_folder, size=(360, 360)):
    thumb_img = cv2.resize(face_img, size, interpolation=cv2.INTER_LANCZOS4)
    thumb_path = os.path.join(output_folder, "thumb.jpg")
    cv2.imwrite(thumb_path, thumb_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return thumb_path

def convert_spherical_to_cube_optimized(input_path, output_folder, size=CUBE_SIZE):
    """
    Optimized version with multiprocessing for cube faces
    """
    pano_img = cv2.imread(input_path)
    if pano_img is None:
        print(f"❌ Cannot read image {input_path}")
        return False

    # Keep original resolution for best quality
    # Only resize if the image is too large and could cause memory errors
    h, w = pano_img.shape[:2]
    if w > 8192 or h > 4096:
        pano_img = resize_panorama_fast(pano_img, 6144, 3072)
    
    # Rotate panorama 180 degrees
    pano_img = cv2.rotate(pano_img, cv2.ROTATE_180)

    os.makedirs(output_folder, exist_ok=True)

    # Use multiprocessing to create cube faces
    with ProcessPoolExecutor(max_workers=min(6, MAX_WORKERS)) as executor:
        face_args = [(pano_img, face, size) for face in face_params.keys()]
        results = list(executor.map(create_cube_face_batch, face_args))

    faces_images = {}
    
    # Save face images
    for face, face_img in results:
        face_img = correct_rotation(face, face_img)
        out_file = os.path.join(output_folder, f"{face}.jpg")
        
        # Use threading to save files
        def save_image(path, img):
            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 100])
        
        threading.Thread(target=save_image, args=(out_file, face_img)).start()
        faces_images[face] = face_img

    # Create preview and thumbnail
    create_preview_image_fast(faces_images, output_folder)
    create_thumbnail_fast(faces_images['pano_f'], output_folder)

    return True

def create_krpano_xml(processed_images, output_folder, title="funny vtour"):
    """
    Create krpano XML file
    """
    # Create panosuser directory directly in output_folder
    panosuser_folder = os.path.join(output_folder, "panosuser")
    os.makedirs(panosuser_folder, exist_ok=True)
    
    doc = minidom.Document()
    root = doc.createElement('krpano')
    root.setAttribute('title', title)
    doc.appendChild(root)

    version = doc.createElement('version')
    version_text = doc.createTextNode(f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    version.appendChild(version_text)
    root.appendChild(version)
    
    include = doc.createElement('include')
    include.setAttribute('url', '/api/phanmengoc/skin/vtourskin.xml')
    include2 = doc.createElement('include')
    include2.setAttribute('url', '/api/phanmengoc/skin/vtourskin_design_flat_light.xml')
    root.appendChild(include)
    root.appendChild(include2)
    
    for img_info in processed_images:
        image_name = img_info['name']
        
        scene = doc.createElement('scene')
        scene.setAttribute('name',f'funny_{image_name}')
        scene.setAttribute('title', image_name)
        scene.setAttribute('onstart', '')
        scene.setAttribute('thumburl', f'panosuser/{image_name}/thumb.jpg')
        scene.setAttribute('lat', '')
        scene.setAttribute('lng', '')
        scene.setAttribute('alt', '')
        scene.setAttribute('heading', '')
        
        control = doc.createElement('control')
        control.setAttribute('bouncinglimits', 'calc:image.cube ? true : false')
        scene.appendChild(control)
        
        view = doc.createElement('view')
        view.setAttribute('hlookat', '0.0')
        view.setAttribute('vlookat', '0.0')
        view.setAttribute('fovtype', 'MFOV')
        view.setAttribute('fov', '120')
        view.setAttribute('maxpixelzoom', '2.0')
        view.setAttribute('fovmin', '70')
        view.setAttribute('fovmax', '140')
        view.setAttribute('limitview', 'auto')
        scene.appendChild(view)
        
        preview = doc.createElement('preview')
        preview.setAttribute('url', f'panosuser/{image_name}/preview.jpg')
        scene.appendChild(preview)
        
        image = doc.createElement('image')
        cube = doc.createElement('cube')
        cube.setAttribute('url', f'panosuser/{image_name}/pano_%s.jpg')
        image.appendChild(cube)
        scene.appendChild(image)
        
        root.appendChild(scene)
    
    root.appendChild(doc.createComment('scene tiếp theo'))
    
    xml_path = os.path.join(output_folder, "user1.xml")
    with open(xml_path, 'w', encoding='utf-8') as f:
        xml_str = doc.toprettyxml(indent='\t')
        f.write(xml_str)
    
    print(f"✅ Created XML file for krpano at {xml_path}")
    return xml_path

def create_krpano_html(output_folder, title="Tools Krpano Funny"):
    """
    Create krpano HTML file
    """
    html_content = f"""<!DOCTYPE html>
<html>
<head>
	<title>{title}</title>
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, viewport-fit=cover" />
	<meta name="apple-mobile-web-app-capable" content="yes" />
	<meta name="apple-mobile-web-app-status-bar-style" content="black" />
	<meta name="mobile-web-app-capable" content="yes" />
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
	<meta http-equiv="x-ua-compatible" content="IE=edge" />
	<style>
		html {{ height:100%; }}
		body {{ height:100%; overflow:hidden; margin:0; padding:0; font-family:Arial, Helvetica, sans-serif; font-size:16px; color:#FFFFFF; background-color:#000000; }}
	</style>
</head>
<body>

<script src="/api/phanmengoc/funny.js"></script>

<div id="pano" style="width:100%;height:100%;">
	<noscript><table style="width:100%;height:100%;"><tr style="vertical-align:middle;"><td><div style="text-align:center;">ERROR:<br/><br/>Javascript not activated<br/><br/></div></td></tr></table></noscript>
	<script>
		embedpano({{xml:"user1.xml", target:"pano", passQueryParameters:"startscene,startlookat"}});
	</script>
</div>

</body>
</html>
"""
    html_path = os.path.join(output_folder, "Toolstour.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created HTML file for krpano at {html_path}")
    return html_path

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

        # Process files using now local functions (not toolfunny)
        processed_images = []
        for input_path in saved_files:
            image_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # Final output path - directly in panosuser folder
            output_path = os.path.join(panosuser_folder, image_name)
            
            # Process image
            success = convert_spherical_to_cube_optimized(input_path, output_path, CUBE_SIZE)
            
            if success:
                processed_images.append({
                    'name': image_name,
                    'input_path': input_path,
                    'output_path': output_path
                })

        # Create XML and HTML if any images were processed successfully
        if processed_images:
            xml_path = create_krpano_xml(processed_images, project_output_dir, project_name)
            html_path = create_krpano_html(project_output_dir, f"Tools Krpano {project_name}")
            
            # Delete usertools folder if it was created automatically
            usertools_path = os.path.join(project_output_dir, "usertools")
            if os.path.exists(usertools_path):
                try:
                    shutil.rmtree(usertools_path)
                    print(f"Deleted unnecessary folder: {usertools_path}")
                except Exception as e:
                    print(f"Could not delete folder {usertools_path}: {str(e)}")
            
            # Delete uploads folder after processing to save space
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Deleted uploads folder: {project_upload_dir}")
            except Exception as e:
                print(f"Could not delete uploads folder {project_upload_dir}: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(processed_images)} images',
                'processed_count': len(processed_images),
                'total_count': len(files),
                'html_path': html_path,
                'project_name': project_name
            })
        else:
            # Delete uploads folder if processing was not successful
            try:
                shutil.rmtree(project_upload_dir)
                print(f"Deleted uploads folder: {project_upload_dir}")
            except Exception as e:
                print(f"Could not delete uploads folder {project_upload_dir}: {str(e)}")
                
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
    return send_from_directory(PHANMENGOC_FOLDER, filename)

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

@app.route('/')
def index():
    """
    Simple health check endpoint
    """
    return jsonify({
        'status': 'ok',
        'message': 'Panorama Processing API is running',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host='0.0.0.0', port=port) 
