import os
import http.server
import socketserver
import socket
import builtins
import qrcode
import io
import urllib.parse
from tqdm import tqdm
from typing import Any

# Explicit builtins to satisfy strict Pylance/IDE rules
print = builtins.print
input = builtins.input
len = builtins.len
str = builtins.str
set = builtins.set
Exception = builtins.Exception
AttributeError = builtins.AttributeError
KeyboardInterrupt = builtins.KeyboardInterrupt
ConnectionAbortedError = builtins.ConnectionAbortedError
ConnectionResetError = builtins.ConnectionResetError
super = builtins.super

PORT = 8000

def get_ip() -> builtins.str:
    """Retrieves the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

class ProgressHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[#] Activity: {args[0]}")

    def do_GET(self):
        if self.path == '/' or self.path == '':
            try:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(self.get_mobile_ui().encode('utf-8'))
                return
            except Exception as e:
                print(f"[X] UI Error: {e}")
        return super().do_GET()

    def get_mobile_ui(self):
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        file_list_html = ""
        for f in files:
            is_vid = f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
            icon = "🎬" if is_vid else "📄"
            safe_name = urllib.parse.quote(f)
            file_list_html += f'''
            <div class="file-card">
                <input type="checkbox" class="file-check" data-url="{safe_name}">
                <div class="file-info" onclick="downloadSingle('{safe_name}')">
                    <span class="icon">{icon}</span>
                    <span class="name">{f}</span>
                </div>
            </div>'''

        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <title>VAULT MOBILE</title>
            <style>
                :root {{ --bg: #050505; --card: #0c0c0c; --accent: #3b82f6; --text: #ffffff; }}
                body {{ font-family: -apple-system, system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
                .header {{ margin-bottom: 20px; border-bottom: 1px solid #111; padding-bottom: 10px; }}
                h2 {{ font-size: 0.9rem; letter-spacing: 5px; color: #333; margin: 0; text-align: center; }}
                .controls {{ position: sticky; top: 0; background: var(--bg); padding: 15px 0; z-index: 100; display: flex; gap: 10px; }}
                .btn {{ background: #0f0f0f; border: 1px solid #222; color: #888; padding: 14px; border-radius: 4px; flex: 1; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; cursor: pointer; }}
                .btn-blue {{ border-color: var(--accent); color: var(--accent); }}
                .file-list {{ display: flex; flex-direction: column; gap: 8px; }}
                .file-card {{ background: var(--card); border: 1px solid #111; border-radius: 4px; display: flex; align-items: center; padding: 14px; }}
                .file-check {{ width: 22px; height: 22px; margin-right: 15px; accent-color: var(--accent); }}
                .file-info {{ flex: 1; display: flex; align-items: center; overflow: hidden; cursor: pointer; }}
                .icon {{ margin-right: 12px; opacity: 0.5; font-size: 1.2rem; }}
                .name {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.85rem; color: #ccc; }}
            </style>
        </head>
        <body>
            <div class="header"><h2>VAULT</h2></div>
            <div class="controls">
                <button class="btn" onclick="toggleAll()">SELECT ALL</button>
                <button class="btn btn-blue" onclick="downloadSelected()">DOWNLOAD SELECTED</button>
            </div>
            <div class="file-list">{file_list_html}</div>
            <script>
                function toggleAll() {{
                    const checks = document.querySelectorAll('.file-check');
                    const anyUnchecked = Array.from(checks).some(c => !c.checked);
                    checks.forEach(c => c.checked = anyUnchecked);
                }}
                function downloadSingle(url) {{
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = decodeURIComponent(url);
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }}
                async function downloadSelected() {{
                    const selected = document.querySelectorAll('.file-check:checked');
                    if(selected.length === 0) return;
                    for(let check of selected) {{
                        downloadSingle(check.dataset.url);
                        await new Promise(r => setTimeout(r, 1500)); 
                    }}
                }}
            </script>
        </body>
        </html>
        '''

    def copyfile(self, source: Any, outputfile: Any):
        try:
            fd = source.fileno()
            file_size = os.fstat(fd).st_size
        except (AttributeError, io.UnsupportedOperation, Exception):
            return super().copyfile(source, outputfile)

        with tqdm(total=file_size, unit='B', unit_scale=True, desc="PORTING", leave=False) as pbar:
            try:
                while True:
                    buf = source.read(1024*64) 
                    if not buf: break
                    outputfile.write(buf)
                    pbar.update(len(buf))
            except (ConnectionAbortedError, ConnectionResetError):
                print("\n[!] Connection lost: Mobile device disconnected.")

def start_server():
    print("\n--- Professional File Porter ---")
    raw_path = input("Drag and drop your FOLDER or FILE here: ").strip()
    
    # Advanced Path Cleaning for PowerShell & CMD
    # Removes leading &, single quotes, and double quotes
    path = raw_path
    if path.startswith('&'):
        path = path[1:].strip()
    path = path.replace("'", "").replace('"', '')

    if os.path.exists(path):
        target_dir = os.path.dirname(path) if os.path.isfile(path) else path
        os.chdir(target_dir)
        
        local_ip = get_ip()
        access_link = f"http://{local_ip}:{PORT}"
        
        qr = qrcode.QRCode(version=1, box_size=1, border=4)
        qr.add_data(access_link)
        qr.make(fit=True)
        
        print("\n[!] SCAN FOR MOBILE ACCESS:")
        qr.print_ascii(invert=True)

        print(f"\n[!] SERVER ONLINE")
        print(f"[!] Target Path: {path}")
        print(f"[!] Access: {access_link}")
        print("--------------------------------------------------")
        
        try:
            with ThreadedHTTPServer(("", PORT), ProgressHandler) as httpd:
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Server stopped by user.")
    else:
        print(f"[X] Invalid Path: {path}")

if __name__ == "__main__":
    start_server()