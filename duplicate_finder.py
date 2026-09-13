import os
import subprocess
import cv2
from PIL import Image
import imagehash
from flask import Flask, render_template_string, request, jsonify, send_file
import threading
import webbrowser

def select_folders_mac():
    """Opens a native macOS folder picker allowing multiple selections."""
    try:
        script = '''
        tell application "Finder"
            activate
        end tell
        
        -- Forces Mac to let you pick more than one
        set myFolders to choose folder with prompt "Select folders to scan for duplicates:" multiple selections allowed true
        
        set posixPaths to {}
        repeat with aFolder in myFolders
            set end of posixPaths to (POSIX path of aFolder)
        end repeat
        
        set AppleScript's text item delimiters to linefeed
        return posixPaths as text
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        paths = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
        return paths
    except subprocess.CalledProcessError:
        return []

def get_file_info(filepath):
    """Gathers file details like size and extension."""
    try:
        size_bytes = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                size_str = f"{size_bytes:.2f} {unit}"
                break
            size_bytes /= 1024.0
        else:
            size_str = f"{size_bytes:.2f} TB"
    except:
        size_str = "Unknown Size"

    ext = filepath.split('.')[-1].lower()
    
    return {
        'path': filepath,
        'name': os.path.basename(filepath),
        'size': size_str,
        'ext': ext,
        'is_video': ext in ['mp4', 'mov', 'webm', 'avi', 'mkv', 'm4v'],
        'can_play_web': ext in ['mp4', 'mov', 'webm', 'm4v']
    }

def get_file_hash(filepath, ext):
    """Generates a perceptual hash for an image or a video."""
    try:
        if ext in ['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v']:
            cap = cv2.VideoCapture(filepath)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames // 2))
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                return str(imagehash.phash(img))
                
        elif ext in ['jpg', 'jpeg', 'png', 'heic', 'webp']:
            img = Image.open(filepath)
            return str(imagehash.phash(img))
            
    except Exception as e:
        pass
    return None

app = Flask(__name__)
duplicates_global = {} 

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Duplicate Finder Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; padding: 20px; }
        .group { background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .grid { display: flex; gap: 20px; flex-wrap: wrap; }
        .card { width: 300px; border: 1px solid #ddd; padding: 15px; border-radius: 8px; text-align: center; background: #fafafa; }
        .card img, .card video { width: 100%; height: 200px; object-fit: contain; border-radius: 4px; background: #000; }
        .unsupported { width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; background: #eee; border-radius: 4px; color: #666; flex-direction: column; }
        .info { font-size: 13px; color: #333; margin: 15px 0; line-height: 1.5; text-align: left; background: #fff; padding: 10px; border: 1px solid #eee; border-radius: 4px; word-break: break-all; }
        button { background: #ff4757; color: white; border: none; padding: 10px; width: 100%; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 14px; }
        button:hover { background: #ff6b81; }
    </style>
    <script>
        // ONE-CLICK DELETION LOGIC
        function deleteFile(filepath, btnElement) {
            // The browser prompt has been removed. 
            // Clicking "Delete" now immediately executes the delete command.
            fetch('/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: filepath})
            }).then(response => response.json())
              .then(data => {
                  if(data.success) {
                      // Remove the card from the grid visually
                      btnElement.closest('.card').style.display = 'none';
                  } else {
                      alert("Failed to delete file. It might have already been moved.");
                  }
              });
        }
    </script>
</head>
<body>
    <h1>Potential Duplicates Found</h1>
    <p>Review the visual matches below. Clicking "Delete" will immediately remove the file from your computer.</p>
    
    {% for hash_val, files in duplicates.items() %}
    <div class="group">
        <h3>Match Group</h3>
        <div class="grid">
            {% for file in files %}
            <div class="card">
                {% if file.is_video %}
                    {% if file.can_play_web %}
                        <video controls preload="metadata">
                            <source src="/serve_file?path={{ file.path }}">
                        </video>
                    {% else %}
                        <div class="unsupported">
                            🎬 {{ file.ext | upper }} Video<br>
                            <span style="font-size: 10px; margin-top: 5px;">(Preview unsupported in browser)</span>
                        </div>
                    {% endif %}
                {% else %}
                    <img src="/serve_file?path={{ file.path }}" alt="preview">
                {% endif %}
                
                <div class="info">
                    <strong>{{ file.name }}</strong><br>
                    <strong>Size:</strong> {{ file.size }}<br>
                    <strong>Type:</strong> {{ file.ext | upper }}<br>
                    <span style="font-size: 11px; color: #777;">{{ file.path }}</span>
                </div>
                
                <button onclick="deleteFile('{{ file.path | replace(\"'\", \"\\\\'\") }}', this)">Delete</button>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE, duplicates=duplicates_global)

@app.route('/serve_file')
def serve_file():
    filepath = request.args.get('path')
    return send_file(filepath, conditional=True)

@app.route('/delete', methods=['POST'])
def delete_file():
    filepath = request.json.get('path')
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return jsonify({"success": True})
        except Exception as e:
            pass
    return jsonify({"success": False})

if __name__ == "__main__":
    print("\n--- Visual Duplicate Finder (One-Click Deletion) ---")
    folders = select_folders_mac()
    
    if not folders:
        print("No folders selected. Canceling.")
        exit()

    print(f"\nScanning {len(folders)} folder(s)...")
    print("Generating visual hashes (this may take a minute for videos)...")

    hashes = {}
    
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if filename.startswith('.'): continue 
                    
                filepath = os.path.join(root, filename)
                file_info = get_file_info(filepath)
                
                if file_info['ext'] in ['jpg', 'jpeg', 'png', 'heic', 'webp', 'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v']:
                    file_hash = get_file_hash(filepath, file_info['ext'])
                    
                    if file_hash:
                        if file_hash not in hashes:
                            hashes[file_hash] = []
                        hashes[file_hash].append(file_info)

    for h, file_list in hashes.items():
        if len(file_list) > 1:
            duplicates_global[h] = file_list

    if not duplicates_global:
        print("\nNo visual duplicates found!")
        exit()

    print(f"\nFound {len(duplicates_global)} groups of duplicates!")
    print("Opening dashboard in your web browser...")
    
    threading.Timer(1.25, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    
    app.run(port=5000)