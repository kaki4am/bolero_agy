#!/usr/bin/env python3
import subprocess
import sys
import io
import os
import qrcode

ARTIFACT_DIR = "/root/.gemini/antigravity-cli/brain/a1f1de14-7e6c-48e9-bed6-b0ad2395fbf8"

def print_qr(uri: str):
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)
    f = io.StringIO()
    qr.print_ascii(out=f, invert=True)
    return f.getvalue()

def save_qr_png(uri: str):
    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    out_path = os.path.join(ARTIFACT_DIR, "signal_link_qr.png")
    img.save(out_path)
    return out_path

def main():
    print("[*] Launching signal-cli link process for 'BoleroBot'...")
    sys.stdout.flush()
    proc = subprocess.Popen(
        ['/usr/local/bin/signal-cli', 'link', '-n', 'BoleroBot'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    uri = None
    for line in proc.stdout:
        line_s = line.strip()
        if 'sgnl://' in line_s or 'tsdevice:/' in line_s or 'linkdevice' in line_s:
            uri = line_s
            print(f"\n[+] LINKING URI DETECTED:\n{uri}\n")
            
            # Save PNG image
            try:
                png_path = save_qr_png(uri)
                print(f"[+] QR Image saved to: {png_path}")
            except Exception as e:
                print(f"[!] PNG save error: {e}")

            print("[+] SCAN THIS QR CODE IN SIGNAL (Settings -> Linked Devices -> Link New Device):\n")
            try:
                ascii_qr = print_qr(uri)
                print(ascii_qr)
            except Exception as e:
                print(f"[!] ASCII render error: {e}")
                
            sys.stdout.flush()
            break
        elif line_s:
            print(line_s)
            sys.stdout.flush()

    if not uri:
        err = proc.stderr.read()
        print(f"[-] Failed to obtain linking URI: {err}")
        return

    print("\n[*] Waiting for phone confirmation... (scan the QR code above on your Signal app)")
    sys.stdout.flush()
    stdout_rest, stderr_rest = proc.communicate()
    if proc.returncode == 0:
        print("\n[SUCCESS] Signal device successfully linked!")
        if stdout_rest:
            print(stdout_rest)
    else:
        print(f"\n[-] signal-cli link failed or timed out (code {proc.returncode}):\n{stderr_rest}")

if __name__ == '__main__':
    main()
