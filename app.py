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
# Cấu hình CORS đơn giản - chỉ để tại một nơi duy nhất
CORS(app, resources={r"/*": {"origins": "*"}})

# Kiểm tra nếu đang chạy trên cloud platform
is_render = os.environ.get("RENDER") or "render" in os.environ.get("RENDER_SERVICE_ID", "") or "render" in os.environ.get("RENDER_INSTANCE_ID", "")
is_cloud = os.environ.get("RAILWAY_ENVIRONMENT") or is_render

# Configure folders based on environment
if is_cloud:
    # Thư mục gốc trên Render
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Trên Railway hoặc Render, sử dụng thư mục /tmp để lưu trữ tạm
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    OUTPUT_FOLDER = os.path.join('/tmp', 'output')
    
    # Thư mục phanmengoc nằm cùng cấp với app.py
    PHANMENGOC_FOLDER = os.path.join(os.getcwd(), 'phanmengoc')
    WEBTOOLS_ROOT = os.getcwd()  # Sử dụng thư mục hiện tại làm webtools root
    
    print(f"Running on cloud platform. Current dir={os.getcwd()}")
    print(f"PHANMENGOC_FOLDER={PHANMENGOC_FOLDER}, exists={os.path.exists(PHANMENGOC_FOLDER)}")
    
    # Đảm bảo thư mục phanmengoc tồn tại và có các file cần thiết
    if not os.path.exists(PHANMENGOC_FOLDER):
        print(f"phanmengoc folder not found at {PHANMENGOC_FOLDER}")
        # Tạo thư mục nếu không tồn tại
        os.makedirs(PHANMENGOC_FOLDER, exist_ok=True)
        print(f"Created empty phanmengoc folder at {PHANMENGOC_FOLDER}")
        
    # Tạo funny.js nếu không tồn tại
    funny_js_path = os.path.join(PHANMENGOC_FOLDER, 'funny.js')
    if not os.path.exists(funny_js_path):
        print(f"Creating funny.js at {funny_js_path}")
        with open(funny_js_path, 'w', encoding='utf-8') as f:
            # Mã JavaScript cần thiết cho panorama viewer
            f.write('''
/*
    krpano Embedding Script
    krpano 1.20.9 (build 2020-02-11)
*/
function embedpano(e){function at(e){return(""+e).toLowerCase()}function ft(e,t){return e[d](t)>=0}function lt(){var e=navigator.platform;var t=navigator.userAgent;var n=at(e);var r=at(t);var i=0;var s=0;i=ft(r,"ipad")|ft(r,"iphone")|ft(r,"ipod")||ft(r,"ipad;")|ft(r,"iphone;")|ft(r,"ipod;")||ft(r,"android")|ft(n,"ipad")|ft(n,"iphone")|ft(n,"ipod")|ft(n,"android");s=i|ft(r,"mobile")|ft(r,"windows ce")||ft(e,"windows ce")||ft(r,"midp")||ft(r,"pocket")||ft(r,"pda")||ft(r,"avantgo")||ft(r,"xv6850")||ft(r,"xv6800")||ft(r,"xv6700")||ft(r,"xv6600")||ft(r,"xv6500")||ft(r,"xv5800")||ft(r,"xv5700")||ft(r,"xv5600")||ft(r,"xv5500")||ft(r,"xv5400")||ft(r,"xv5300")||ft(r,"xv5200")||ft(r,"xv5100")||ft(r,"xv4100")||ft(r,"xv3650")||ft(r,"xv3500")||ft(r,"xv3300")||ft(r,"xv3200")||ft(r,"xv3000")||ft(r,"xv2800")||ft(r,"xv2600")||ft(r,"xv2500")||ft(r,"xv2000")||ft(r,"xv1700")||ft(r,"xv1600")||ft(r,"xv1500")||ft(r,"xv1200")||ft(r,"xv1000")||ft(r,"xv700")||ft(r,"xv6")||ft(r,"xv4")||ft(r,"xv3")||ft(r,"xv")||ft(r,"asus-galaxy")||ft(r,"nokia")||ft(n,"smartphone")||ft(n,"android")||ft(n,"blackberry")||ft(n,"windows ce")||ft(n,"windows phone");return{isAndroid:ft(r,"android"),isIOS:ft(r,/iP(ad|hone|od)/i),isMobile:s,isPhone:s&&!ft(r,"tablet"),isTablet:s&&ft(r,"tablet"),isDesktop:!(s||i&&!ft(r,"tablet"))}}function ct(){var e=Lt.createElement("div");e.innerHTML="<div style='-webkit-tap-highlight-color:rgba(0,0,0,0);-ms-touch-action:none;touch-action:none;'></div>";var t=e.firstChild;if(t&&typeof t.style.touchAction!="undefined"){t.style.touchAction="none"}if(t&&typeof t.style.msTouchAction!="undefined"){t.style.msTouchAction="none"}}function ht(e){var t="knoyx-";if(e&&e.length>0){for(var n=0;n<e.length;n++){var r=e[n];if(typeof r==="string"){if(r.indexOf(t)==0){var i=r.slice(t.length);Gt.vars[i[0]]=i.slice(1)}}}}ht.instance=new ht}function pt(){var e=Lt.createElement("canvas");return!(!e.getContext||!e.getContext("2d"))}function dt(e){return typeof e!=="undefined"}function vt(e){if(dt(e))return e}function mt(){var e=navigator.pointerEnabled;var t=navigator.msPointerEnabled;var n=!1;var r=!1;var i=navigator.maxTouchPoints>1||navigator.msMaxTouchPoints>1;var s=e||t;var o=i;var u=navigator.appVersion;var a=at(navigator.userAgent);var f=navigator.platform;var l=at(f);var c=navigator.vendor;try{r=window.top&&window.top!=window.self}catch(h){r=true}n="MacIntel"==f&&navigator["userAgent"].indexOf("Safari")>=0&&navigator["userAgent"].indexOf("Mobile")>=0;var p=0;var d=0;var v="none";var m="none";var g="absolute";var y="none";var b="auto";var w="static";var E="center";var S="0";var x="0";var T="10px";var N="none";var C="none";var k="";var L="0px";var A="0px";var O="0px";var M="0px";var _=!r;var D=!r;var P=true;var H="fill";var B=true;var j=true;var F=false;var I=true;var q=false;var R=true;var U=!0;var z=at(navigator.userAgent);z=z.indexOf("mobile")>=0;if(z)z=z.indexOf("firefox")<0;if(z){v="rgba(0,0,0,0.4)";m="rgba(0,0,0,0.2)";if(!J.isAndroid&&!J.isIOS){v="rgba(0,0,0,0.8)";m="rgba(0,0,0,0.4)"}g="relative";p=144;y="100%";b="hidden";w="absolute";E="absolute";S="16px";x="16px";T="10px";N="none";C="none";k="4px";L="8px";A="8px";O="18px";M="18px";d=1;_=false;if(J.isIOS){q=true}if(J.isPhone&&!q){P=false}D=false;j=false;H="contain"}if(J.isDesktop){F=true}var W=J.isDesktop?40:24;var X=J.isDesktop?40:24;var V="24px";var $="24px";if(J.isIOS==false&&J.isAndroid==false&&J.isDesktop==false){U=!1}var K=z?"no-select":"auto";var G=z?"0px":"auto";return{bgcolor:"#000000",linear:J.isDesktop,roundedges:6,wmode:"opaque",localfocus:I,locallimit:P,localcursor:U,touchdevice:i,androidstock:false,useCSS3D:R,disablewheel:false,errorcorner:"tl",hotspot_day:"000000"+"*0.3"+"*1"+"*0.3"+"*Verdana"+"*10"+"*center"+"*"+K+"*none",hotspot_night:"000000"+"*0.3"+"*1"+"*0.3"+"*Verdana"+"*10"+"*center"+"*"+K+"*none",layout:{standard:{touch:"false",align:"center",x:0,y:0},fullscreen:{touch:"true",align:"center",x:0,y:0},androidstock:{touch:"true",align:"center",x:0,y:0},css3d:{touch:"false",align:"center",x:0,y:0},webvr:{touch:"true",align:"center",x:0,y:0},area:{touch:"false",align:"center",x:0,y:0}},control:{mousemode:"drag",dragrelative:F,dragfriction:.9,movetoaccelerate:1,movetospeed:10,movetofriction:.8,keycodesin:"83|40|34",keycodesout:"87|38|33",keycodesinforces:2,keycodesoutforces:2,rheightscale:0,tilttowalk:.5},image:{lamp_normal:"https://raw.githubusercontent.com/bbkincso/ff/master/panorama-json/krpano/loading-opaque.png",lamp_wait:"https://raw.githubusercontent.com/bbkincso/ff/master/panorama-json/krpano/loading-opaque.png"},plugin:{logo:{align:"leftbottom",alpha:.75,scale:1,url:"",vr:true},logokeep:{align:"lefttop",scale:1,url:"",visible:true,vr:false,keep:true},autorotation:{enabled:false,waittime:1.5,accel:1,speed:3,horizon:0,tofov:null,rotate:true},zoomtocursor:{autoenable:true,enabled:false,speed:6,zoomspeed:3},gyro:{enabled:true,vr:true},webvr:{mobilevr_support:R,mobilevr_fake_support:false,mouse_mode:"drag",zoom:true,zoompow:1.6,headtouch_scrollbutton:true,camroll:false,multireslock:true,sensorrate:50,mask:true,maxfov:120,bigscreenstyle:false},editor:{})},<script>
var settings = {};
settings.localpath = "false";
function initServer(){
    window.addEventListener("pageshow", enterframe, false);
}
var g_tilt;
function enterframe(e){}

var krpano = null;
function registerkrpanointerface(){
  krpano = document.getElementById("krpanoSWFObject");
  if (krpano && krpano.interface) {
   g_tilt = navigator.userAgent.toLowerCase().indexOf('iphone') >= 0 || navigator.userAgent.toLowerCase().indexOf('ipad') >= 0 || navigator.userAgent.toLowerCase().indexOf('ipod') >= 0;
    if (localStorage.getItem('gyroOn') === 'false') {
      krpano.set("plugin[gyro].enabled", false);
      localStorage.setItem('gyroOn', 'false');
    }
  } else {
    setTimeout("registerkrpanointerface()", 100);
  }
}
            ''')
        print(f"Created funny.js file")
        
    # Tạo thư mục skin nếu cần
    skin_folder = os.path.join(PHANMENGOC_FOLDER, 'skin')
    if not os.path.exists(skin_folder):
        os.makedirs(skin_folder, exist_ok=True)
        print(f"Created skin folder at {skin_folder}")
        
        # Tạo file vtourskin.xml cơ bản
        vtourskin_path = os.path.join(skin_folder, 'vtourskin.xml')
        with open(vtourskin_path, 'w', encoding='utf-8') as f:
            f.write('<krpano><style name="skin_base" /></krpano>')
        
        # Tạo file vtourskin_design_flat_light.xml cơ bản
        design_path = os.path.join(skin_folder, 'vtourskin_design_flat_light.xml')
        with open(design_path, 'w', encoding='utf-8') as f:
            f.write('<krpano><style name="skin_design" /></krpano>')

    # Tạo thư mục plugins nếu cần
    plugins_folder = os.path.join(PHANMENGOC_FOLDER, 'plugins')
    if not os.path.exists(plugins_folder):
        os.makedirs(plugins_folder, exist_ok=True)
        print(f"Created plugins folder at {plugins_folder}")
        
        # Tạo webvr.js tối thiểu trong thư mục plugins
        webvr_js_path = os.path.join(plugins_folder, 'webvr.js')
        with open(webvr_js_path, 'w', encoding='utf-8') as f:
            f.write('''
/*
    WebVR plugin for krpano
*/
var krpanoplugin = function() {
    // Plugin code
    console.log("WebVR plugin loaded");
};
            ''')
            
        # Tạo webvr.xml tối thiểu trong thư mục plugins
        webvr_xml_path = os.path.join(plugins_folder, 'webvr.xml')
        with open(webvr_xml_path, 'w', encoding='utf-8') as f:
            f.write('<krpano><plugin name="webvr" /></krpano>')
else:
    # Local development
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    WEBTOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PHANMENGOC_FOLDER = os.path.join(WEBTOOLS_ROOT, "phanmengoc")

# Tạo thư mục nếu chưa tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Constants moved from toolfunny.py
CUBE_SIZE = 1024  # Giảm kích thước mặc định xuống 1024 (thay vì 1920) để tiết kiệm bộ nhớ

# Giới hạn số lượng worker dựa trên môi trường
if is_cloud:
    MAX_WORKERS = 2  # Giảm xuống 2 worker trên môi trường cloud
else:
    MAX_WORKERS = min(cpu_count(), 8)  # Sử dụng tối đa 8 worker trong môi trường local

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
    Optimized version with improved error handling and resource management
    """
    try:
        print(f"Starting processing of {input_path}")
        pano_img = cv2.imread(input_path)
        if pano_img is None:
            print(f"❌ Cannot read image {input_path}")
            return False

        # Resize to smaller dimensions on cloud
        h, w = pano_img.shape[:2]
        print(f"Original image size: {w}x{h}")
        
        # Always resize on cloud to save memory
        if is_cloud or w > 4096 or h > 2048:
            target_width = 4096
            target_height = 2048
            print(f"Resizing to {target_width}x{target_height} to save memory")
            pano_img = resize_panorama_fast(pano_img, target_width, target_height)

        # Rotate panorama 180 degrees
        pano_img = cv2.rotate(pano_img, cv2.ROTATE_180)

        os.makedirs(output_folder, exist_ok=True)

        # Process faces sequentially on cloud instead of using multiprocessing
        if is_cloud:
            print("Processing cube faces sequentially (cloud mode)")
            faces_images = {}
            for face in face_params.keys():
                try:
                    print(f"Processing face: {face}")
                    face_img = create_cube_face_optimized(pano_img, face, size)
                    face_img = correct_rotation(face, face_img)
                    out_file = os.path.join(output_folder, f"{face}.jpg")
                    cv2.imwrite(out_file, face_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    faces_images[face] = face_img
                    print(f"✅ Saved face {face}")
                except Exception as e:
                    print(f"❌ Error processing face {face}: {str(e)}")
        else:
            # Use multiprocessing on local environment
            print("Processing cube faces with multiprocessing")
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
        print("Creating preview image")
        create_preview_image_fast(faces_images, output_folder)
        print("Creating thumbnail")
        create_thumbnail_fast(faces_images['pano_f'], output_folder)
        
        print(f"✅ Successfully processed {input_path}")
        return True
    except Exception as e:
        print(f"❌ Error in convert_spherical_to_cube_optimized: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

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
        # Ghi log bắt đầu xử lý
        print("==== Starting image processing request ====")
        
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400

        project_name = request.form.get('projectName', 'default_project')
        files = request.files.getlist('files[]')
        print(f"Project name: {project_name}, File count: {len(files)}")

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
        print(f"Saving uploaded files to {project_upload_dir}")
        saved_files = []
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(project_upload_dir, filename)
                file.save(file_path)
                saved_files.append(file_path)
                print(f"Saved file: {filename}")

        if not saved_files:
            return jsonify({'error': 'Failed to save files'}), 500

        # Process files - limit to 3 files at a time on cloud to avoid memory issues
        processed_images = []
        max_files = 3 if is_cloud else len(saved_files)
        
        print(f"Processing {min(max_files, len(saved_files))} files at a time")
        
        for i, input_path in enumerate(saved_files[:max_files]):
            try:
                image_name = os.path.splitext(os.path.basename(input_path))[0]
                print(f"Processing file {i+1}/{len(saved_files[:max_files])}: {image_name}")
                
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
                    print(f"Successfully processed {image_name}")
                else:
                    print(f"Failed to process {image_name}")
            except Exception as e:
                print(f"Error processing file {input_path}: {str(e)}")
                import traceback
                traceback.print_exc()

        # Create XML and HTML if any images were processed successfully
        if processed_images:
            print("Creating XML and HTML files")
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
            
            print("==== Completed image processing successfully ====")
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
            
            print("==== Failed to process any images ====")
            return jsonify({'error': 'No images were processed successfully'}), 500

    except Exception as e:
        print(f"==== Critical error in process_images: {str(e)} ====")
        import traceback
        traceback.print_exc()
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
def serve_output_fixed(filename):
    # Đường dẫn đến file trong thư mục output
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    # Nếu là file HTML, kiểm tra và sửa đổi nếu cần
    if filename.lower().endswith('.html'):
        print(f"Serving HTML file: {file_path}")
        
        try:
            # Kiểm tra xem file có tồn tại không
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return f"File not found: {filename}", 404
            
            # Đọc nội dung file HTML
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Kiểm tra xem file HTML có script tag cho funny.js không
            if 'funny.js' in content.lower() or 'Funny.js' in content:
                # Đã có script tag, trả về nội dung gốc
                return content
            else:
                # Thêm script tag cho funny.js
                new_content = content.replace('</head>', 
                    '<script src="/api/phanmengoc/Funny.js"></script>\n</head>')
                
                # Trả về nội dung đã sửa
                return new_content
                
        except Exception as e:
            print(f"Error serving fixed HTML: {str(e)}")
            return str(e), 500
    
    # Nếu không phải file HTML, phục vụ như thông thường
    try:
        return send_from_directory(OUTPUT_FOLDER, filename)
    except Exception as e:
        print(f"Error serving output file: {str(e)}")
        return str(e), 500

@app.route('/api/phanmengoc/<path:filename>')
def serve_phanmengoc(filename):
    print(f"Serving file from phanmengoc: {filename}")
    
    # Chú ý: Funny.js với chữ F viết hoa, nhưng funny.js với chữ f viết thường
    # Đảm bảo xử lý cả 2 trường hợp
    if filename.lower() == 'funny.js':
        try:
            # Tìm kiếm file funny.js không phân biệt hoa thường
            for f in os.listdir(PHANMENGOC_FOLDER):
                if f.lower() == 'funny.js':
                    print(f"Found file: {f}")
                    return send_from_directory(PHANMENGOC_FOLDER, f)
            
            # Nếu không tìm thấy, trả về file funny.js đã tạo
            print(f"Using default funny.js")
            return send_from_directory(PHANMENGOC_FOLDER, 'funny.js')
        except Exception as e:
            print(f"Error serving funny.js: {str(e)}")
            return str(e), 500
    
    # Trường hợp các file khác
    try:
        if os.path.exists(os.path.join(PHANMENGOC_FOLDER, filename)):
            return send_from_directory(PHANMENGOC_FOLDER, filename)
        else:
            # Log lỗi khi không tìm thấy file
            print(f"File not found: {os.path.join(PHANMENGOC_FOLDER, filename)}")
            subfolder_path = os.path.dirname(os.path.join(PHANMENGOC_FOLDER, filename))
            if os.path.exists(subfolder_path):
                print(f"Subfolder exists, listing files: {os.listdir(subfolder_path)}")
            return f"File not found: {filename}", 404
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        return str(e), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """
    Lấy danh sách tất cả các dự án đã xử lý
    """
    try:
        projects = []
        # Đường dẫn thư mục output mới và cũ
        output_folders = [OUTPUT_FOLDER]
        
        # Thêm đường dẫn thư mục cũ nếu khác với thư mục mới và tồn tại
        old_output_folder = os.path.join(os.getcwd(), 'output')
        if old_output_folder != OUTPUT_FOLDER and os.path.exists(old_output_folder):
            output_folders.append(old_output_folder)
            
        # Thêm đường dẫn thư mục trên Render
        render_output_folder = '/opt/render/project/src/output'
        if render_output_folder != OUTPUT_FOLDER and render_output_folder != old_output_folder and os.path.exists(render_output_folder):
            output_folders.append(render_output_folder)
            
        print(f"Searching for projects in folders: {output_folders}")
            
        # Lấy danh sách dự án từ tất cả các thư mục output
        for output_folder in output_folders:
            if not os.path.exists(output_folder):
                continue
                
            for project_name in os.listdir(output_folder):
                project_dir = os.path.join(output_folder, project_name)
                
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
                            # Lấy đường dẫn tương đối với thư mục output hiện tại
                            # Sử dụng OUTPUT_FOLDER cho đường dẫn API trả về
                            rel_path = os.path.relpath(thumb_path, project_dir)
                            thumbnail_url = f'/api/output/{project_name}/{rel_path}'
                            print(f"Found thumbnail for project {project_name}: {thumbnail_url}")
                
                # Đảm bảo không trùng lặp dự án
                project_exists = any(p['name'] == project_name for p in projects)
                if not project_exists:
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

# Endpoint mới để kiểm tra các thư mục và tệp
@app.route('/api/checkfile', methods=['GET'])
def check_file():
    try:
        # Thu thập thông tin về các thư mục chính
        folders = {
            'upload_folder': {
                'path': UPLOAD_FOLDER,
                'exists': os.path.exists(UPLOAD_FOLDER),
                'is_dir': os.path.isdir(UPLOAD_FOLDER),
                'contents': os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
            },
            'output_folder': {
                'path': OUTPUT_FOLDER,
                'exists': os.path.exists(OUTPUT_FOLDER),
                'is_dir': os.path.isdir(OUTPUT_FOLDER),
                'contents': os.listdir(OUTPUT_FOLDER) if os.path.exists(OUTPUT_FOLDER) else []
            },
            'phanmengoc_folder': {
                'path': PHANMENGOC_FOLDER,
                'exists': os.path.exists(PHANMENGOC_FOLDER),
                'is_dir': os.path.isdir(PHANMENGOC_FOLDER),
                'contents': os.listdir(PHANMENGOC_FOLDER) if os.path.exists(PHANMENGOC_FOLDER) else []
            },
            'webtools_root': {
                'path': WEBTOOLS_ROOT,
                'exists': os.path.exists(WEBTOOLS_ROOT),
                'is_dir': os.path.isdir(WEBTOOLS_ROOT)
            },
            'current_directory': {
                'path': os.path.abspath('.'),
                'exists': True,
                'contents': os.listdir('.')
            },
            'environment': {
                'railway': bool(os.environ.get("RAILWAY_ENVIRONMENT")),
                'tmp_dir_exists': os.path.exists('/tmp'),
                'working_dir': os.getcwd()
            }
        }

        # Kiểm tra quyền truy cập các thư mục
        access_info = {}
        for name, folder in folders.items():
            if folder.get('exists') and folder.get('is_dir'):
                path = folder.get('path')
                try:
                    # Kiểm tra quyền đọc
                    if path:  # Đảm bảo path không phải None
                        readable = os.access(path, os.R_OK)
                        # Kiểm tra quyền ghi 
                        writable = os.access(path, os.W_OK)
                        access_info[name] = {
                            'readable': readable,
                            'writable': writable
                        }
                    else:
                        access_info[name] = {
                            'error': 'Path is None'
                        }
                except Exception as e:
                    access_info[name] = {
                        'error': str(e)
                    }

        return jsonify({
            'success': True,
            'folders': folders,
            'access_info': access_info,
            'message': 'Kiểm tra thành công'
        })

    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

# Phục vụ file Funny.js đặc biệt (với chữ F viết hoa)
@app.route('/api/phanmengoc/Funny.js')
def serve_funny_js():
    print("Serving Funny.js (uppercase F)")
    try:
        # Trả về file funny.js từ thư mục phanmengoc
        return send_from_directory(PHANMENGOC_FOLDER, 'funny.js')
    except Exception as e:
        print(f"Error serving Funny.js: {str(e)}")
        return str(e), 500

# Hàm kiểm tra tất cả các file và thư mục
@app.route('/api/phanmengoc/checkfiles')
def check_phanmengoc_files():
    result = {
        'phanmengoc_exists': os.path.exists(PHANMENGOC_FOLDER),
        'phanmengoc_path': PHANMENGOC_FOLDER,
        'current_dir': os.getcwd(),
        'files': []
    }
    
    if os.path.exists(PHANMENGOC_FOLDER):
        for root, dirs, files in os.walk(PHANMENGOC_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, PHANMENGOC_FOLDER)
                result['files'].append({
                    'path': relative_path,
                    'size': os.path.getsize(file_path)
                })
    
    return jsonify(result)

# Xem nội dung file HTML
@app.route('/api/viewhtml/<path:filename>')
def view_html_content(filename):
    # Đường dẫn đến file trong thư mục output
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    try:
        # Kiểm tra xem file có tồn tại không
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return jsonify({
                'error': 'File not found',
                'path': file_path,
                'exists': False
            }), 404
        
        # Đọc nội dung file HTML
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Trả về thông tin chi tiết về file
        return jsonify({
            'filename': filename,
            'path': file_path,
            'size': os.path.getsize(file_path),
            'content': content,
            'has_funny_js': 'funny.js' in content.lower() or 'Funny.js' in content,
            'has_webvr': 'webvr.js' in content.lower(),
            'has_embedpano': 'embedpano' in content
        })
            
    except Exception as e:
        print(f"Error viewing HTML: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500
