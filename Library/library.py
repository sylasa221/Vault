import os, json, shutil, threading, sys, builtins
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, 'movies')
THUMB_DIR = os.path.join(BASE_DIR, 'thumbnails')
DATA_FILE = os.path.join(BASE_DIR, 'library_data.json')
HISTORY_FILE = os.path.join(BASE_DIR, 'play_history.json')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'templates', 'index.html')

# Builtin mappings for strict environments
len = builtins.len
enumerate = builtins.enumerate
print = builtins.print
Exception = builtins.Exception

executor = ThreadPoolExecutor(max_workers=4)
window = None

for d in [VIDEO_DIR, THUMB_DIR]:
    if not os.path.exists(d): os.makedirs(d)

def get_json_data(filepath):
    if os.path.exists(filepath):
        try:
            with builtins.open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_json_data(filepath, data):
    with builtins.open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

def open_folder_dialog():
    import webview
    file_types = ('Video Files (*.mp4)', 'All files (*.*)')
    res = window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
    if res:
        def scan():
            found = []
            for path in res:
                if path.lower().endswith('.mp4'):
                    name = os.path.splitext(os.path.basename(path))[0]
                    found.append({"name": name, "path": path})
            window.evaluate_js(f"showImportPanel({json.dumps(found)})")
        executor.submit(scan)

def import_files(file_list):
    def run_import():
        total = len(file_list)
        for i, f in enumerate(file_list):
            dest = os.path.join(VIDEO_DIR, os.path.basename(f['path']))
            window.evaluate_js(f"updateProgress({i+1}, {total}, '{f['name']}')")
            try:
                shutil.copy2(f['path'], dest)
            except Exception as e:
                print(f"Error: {e}")
        window.evaluate_js("finishImport()")
    executor.submit(run_import)

def set_thumbnail(filename):
    import webview
    file_filters = ('Image Files (*.jpg;*.jpeg;*.png;*.webp;*.gif;*.bmp)', 'All files (*.*)')
    res = window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_filters)
    if res:
        def proc(src, name):
            try:
                ext = os.path.splitext(src)[1]
                t_name = f"thumb_{name.replace(' ', '_')}{ext}"
                shutil.copy2(src, os.path.join(THUMB_DIR, t_name))
                thumbs = get_json_data(DATA_FILE)
                thumbs[name] = f"/thumb/{t_name}"
                save_json_data(DATA_FILE, thumbs)
                window.evaluate_js("loadLibrary()")
            except Exception as e:
                print(f"Thumb Error: {e}")
        executor.submit(proc, res[0], filename)

def toggle_fs():
    if window: window.toggle_fullscreen()

def create_app():
    from flask import Flask, send_from_directory, render_template_string, jsonify, request
    app = Flask(__name__)
    @app.route('/')
    def index():
        with builtins.open(TEMPLATE_FILE, 'r', encoding='utf-8') as f: return render_template_string(f.read())
    @app.route('/api/videos')
    def list_vids():
        history, thumbs = get_json_data(HISTORY_FILE), get_json_data(DATA_FILE)
        vids = []
        if os.path.exists(VIDEO_DIR):
            for f in os.listdir(VIDEO_DIR):
                if f.lower().endswith('.mp4'):
                    vids.append({"filename": f, "display_name": os.path.splitext(f)[0], "last_pos": history.get(f, 0), "thumbnail": thumbs.get(f, "")})
        return jsonify(vids)
    @app.route('/api/save_pos', methods=['POST'])
    def save_p():
        d = request.json
        h = get_json_data(HISTORY_FILE)
        h[d['filename']] = d['pos']
        save_json_data(HISTORY_FILE, h)
        return jsonify({"status": "ok"})
    @app.route('/video/<path:f>')
    def serve_video(f): return send_from_directory(VIDEO_DIR, f)
    @app.route('/thumb/<path:f>')
    def serve_thumb(f): return send_from_directory(THUMB_DIR, f)
    return app

if __name__ == '__main__':
    app = create_app()
    threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5000), daemon=True).start()
    import webview
    window = webview.create_window('VAULT', 'http://127.0.0.1:5000', width=1200, height=800)
    window.expose(set_thumbnail, toggle_fs, open_folder_dialog, import_files)
    webview.start(lambda: window.evaluate_js("loadLibrary()"))