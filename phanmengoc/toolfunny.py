import cv2
import numpy as np
import os
from math import pi, atan2, asin
from glob import glob
import argparse
import sys
import xml.dom.minidom as minidom
import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
import threading
from functools import partial
import tkinter as tk
from tkinter import filedialog
import shutil

CUBE_SIZE = 1920
MAX_WORKERS = min(cpu_count(), 8)  # Giới hạn số worker để tránh quá tải RAM

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
    Resize panorama với tỷ lệ cao hơn để cải thiện chất lượng
    """
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)

def vector_to_spherical(x, y, z):
    theta = atan2(x, z)  # longitude
    phi = asin(y)        # latitude
    return theta, phi

def create_cube_face_optimized(pano_img, face, size):
    """
    Tối ưu hóa việc tạo cube face bằng cách sử dụng numpy vectorization
    """
    h, w = pano_img.shape[:2]
    
    # Tạo grid coordinates một lần
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
    Tạo preview nhanh hơn với threading và chất lượng cao hơn
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

    # Sử dụng threading để resize parallel
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
    Phiên bản tối ưu với multiprocessing cho các cube faces
    """
    pano_img = cv2.imread(input_path)
    if pano_img is None:
        print(f"❌ Không đọc được ảnh {input_path}")
        return False

    # Giữ nguyên độ phân giải ảnh để chất lượng tốt nhất
    # Chỉ resize nếu ảnh quá lớn và có thể gây lỗi bộ nhớ
    h, w = pano_img.shape[:2]
    if w > 8192 or h > 4096:
        pano_img = resize_panorama_fast(pano_img, 6144, 3072)
    
    # Xoay lật pano 180 độ
    pano_img = cv2.rotate(pano_img, cv2.ROTATE_180)

    os.makedirs(output_folder, exist_ok=True)

    # Sử dụng multiprocessing để tạo các cube faces
    with ProcessPoolExecutor(max_workers=min(6, MAX_WORKERS)) as executor:
        face_args = [(pano_img, face, size) for face in face_params.keys()]
        results = list(executor.map(create_cube_face_batch, face_args))

    faces_images = {}
    
    # Lưu các face images
    for face, face_img in results:
        face_img = correct_rotation(face, face_img)
        out_file = os.path.join(output_folder, f"{face}.jpg")
        
        # Sử dụng threading để lưu file
        def save_image(path, img):
            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 100])
        
        threading.Thread(target=save_image, args=(out_file, face_img)).start()
        faces_images[face] = face_img

    # Tạo preview và thumbnail
    create_preview_image_fast(faces_images, output_folder)
    create_thumbnail_fast(faces_images['pano_f'], output_folder)

    return True

def process_single_image(args):
    """
    Wrapper function để xử lý một ảnh trong multiprocessing
    """
    input_path, panosuser_folder, size = args
    
    image_name = os.path.splitext(os.path.basename(input_path))[0]
    output_dir = os.path.join(panosuser_folder, image_name)
    
    print(f"🛠 Đang xử lý {input_path}")
    success = convert_spherical_to_cube_optimized(input_path, output_dir, size)
    
    if success:
        return {
            'name': image_name,
            'input_path': input_path,
            'output_path': output_dir
        }
    return None

def create_krpano_xml(processed_images, output_folder, title="funny vtour"):
    """
    Tạo file XML krpano
    """
    # Tạo thư mục cho panosuser ngay trong output_folder
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
    
    print(f"✅ Đã tạo file XML cho krpano tại {xml_path}")
    return xml_path

def create_krpano_html(output_folder, title="Tools Krpano Funny"):
    """
    Tạo file HTML krpano
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
    
    print(f"✅ Đã tạo file HTML cho krpano tại {html_path}")
    return html_path

def batch_convert_optimized(input_folder, output_folder, size=CUBE_SIZE, title="funny vtour"):
    """
    Phiên bản tối ưu với multiprocessing cho batch processing
    """
    supported = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
    files = []
    for ext in supported:
        files += glob(os.path.join(input_folder, ext))
    
    # Loại bỏ các file trùng lặp
    files = list(set(files))

    if not files:
        print("❌ Không tìm thấy ảnh panorama trong thư mục.")
        return

    print(f"📁 Tìm thấy {len(files)} ảnh. Đang xử lý với {MAX_WORKERS} workers...")

    # Tạo thư mục panosuser trong output_folder
    panosuser_folder = os.path.join(output_folder, "panosuser")
    os.makedirs(panosuser_folder, exist_ok=True)

    # Sử dụng multiprocessing để xử lý nhiều ảnh cùng lúc
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        process_args = [(f, panosuser_folder, size) for f in files]
        results = list(executor.map(process_single_image, process_args))

    # Lọc kết quả thành công
    processed_images = [r for r in results if r is not None]
    
    # Tạo XML và HTML
    if processed_images:
        xml_path = create_krpano_xml(processed_images, output_folder, title)
        html_path = create_krpano_html(output_folder, f"Tools Krpano {title}")
        
        # Xóa thư mục usertools nếu nó được tạo tự động
        usertools_path = os.path.join(output_folder, "usertools")
        if os.path.exists(usertools_path):
            try:
                shutil.rmtree(usertools_path)
                print(f"✅ Đã xóa thư mục không cần thiết: {usertools_path}")
            except Exception as e:
                print(f"⚠️ Không thể xóa thư mục {usertools_path}: {str(e)}")
                
        print(f"🎉 Đã xử lý xong {len(processed_images)}/{len(files)} ảnh panorama")
    else:
        print("⚠️ Không có ảnh nào được xử lý thành công")

def is_image_file(file_path):
    """Check if file is an image based on extension"""
    if not os.path.isfile(file_path):
        return False
    _, ext = os.path.splitext(file_path.lower())
    return ext in ['.jpg', '.jpeg', '.png']

def select_input_with_dialog():
    """
    Hiển thị hộp thoại để chọn file hoặc thư mục đầu vào
    """
    root = tk.Tk()
    root.withdraw()  # Ẩn cửa sổ chính
    
    choice = input("Chọn loại đầu vào (1: File ảnh, 2: Thư mục chứa ảnh): ")
    
    if choice == "1":
        # Chọn file ảnh
        filetypes = [
            ("Image files", "*.jpg;*.jpeg;*.png"),
            ("JPEG files", "*.jpg;*.jpeg"),
            ("PNG files", "*.png"),
            ("All files", "*.*")
        ]
        input_path = filedialog.askopenfilename(
            title="Chọn ảnh panorama",
            filetypes=filetypes
        )
    else:
        # Chọn thư mục
        input_path = filedialog.askdirectory(
            title="Chọn thư mục chứa ảnh panorama"
        )
    
    if input_path:
        return input_path
    else:
        print("❌ Không có đầu vào nào được chọn.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chuyển đổi ảnh panorama sang các mặt của hình lập phương (Tối ưu hóa)")
    parser.add_argument("input", help="Đường dẫn đến ảnh panorama hoặc thư mục chứa ảnh", nargs="?", default=None)
    parser.add_argument("-size", type=int, default=CUBE_SIZE, help=f"Kích thước mỗi mặt (mặc định: {CUBE_SIZE})")
    parser.add_argument("-title", type=str, default="funny vtour", help="Tiêu đề cho tour (mặc định: funny vtour)")
    parser.add_argument("-workers", type=int, default=MAX_WORKERS, help=f"Số worker xử lý (mặc định: {MAX_WORKERS})")
    parser.add_argument("-dialog", action="store_true", help="Sử dụng hộp thoại để chọn đầu vào")
    
    args = parser.parse_args()
    input_path = args.input
    tour_title = args.title
    MAX_WORKERS = min(args.workers, cpu_count())
    
    # Sử dụng hộp thoại nếu được yêu cầu hoặc không có đầu vào
    if args.dialog or input_path is None:
        input_path = select_input_with_dialog()
    
    print(f"🚀 Sử dụng {MAX_WORKERS} workers để xử lý")
    
    if os.path.isdir(input_path):
        print(f"🔍 Xử lý thư mục: {input_path}")
        output_folder = "./funnypanos"
        batch_convert_optimized(input_path, output_folder, args.size, tour_title)
    elif is_image_file(input_path):
        print(f"🔍 Xử lý ảnh đơn: {input_path}")
        output_folder = "./output_cubes"
        image_name = os.path.splitext(os.path.basename(input_path))[0]
        
        # Tạo thư mục panosuser trực tiếp trong output_folder
        panosuser_folder = os.path.join(output_folder, "panosuser")
        os.makedirs(panosuser_folder, exist_ok=True)
        
        output_path = os.path.join(panosuser_folder, image_name)
        success = convert_spherical_to_cube_optimized(input_path, output_path, args.size)
        
        if success:
            processed_images = [{
                'name': image_name,
                'input_path': input_path,
                'output_path': output_path
            }]
            xml_path = create_krpano_xml(processed_images, output_folder, tour_title)
            html_path = create_krpano_html(output_folder, f"Tools Krpano {tour_title}")
            
            # Xóa thư mục usertools nếu nó được tạo tự động
            usertools_path = os.path.join(output_folder, "usertools")
            if os.path.exists(usertools_path):
                try:
                    shutil.rmtree(usertools_path)
                    print(f"✅ Đã xóa thư mục không cần thiết: {usertools_path}")
                except Exception as e:
                    print(f"⚠️ Không thể xóa thư mục {usertools_path}: {str(e)}")
            
            print(f"🎉 Ảnh đã được xử lý thành công")
    else:
        print(f"❌ Không tìm thấy ảnh hoặc thư mục: {input_path}")
        sys.exit(1)