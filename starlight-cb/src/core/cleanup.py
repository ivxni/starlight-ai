"""
Process Cleanup Utility
Clears zombie processes that may cause performance issues
"""

import os
import gc
import subprocess


def kill_zombie_processes():
    """Kill old Python/FFmpeg processes that might be hanging"""
    killed = []
    
    try:
        # Get current process ID to avoid killing ourselves
        current_pid = os.getpid()
        
        # Kill old ffmpeg processes (used by OpenCV for UDP streams)
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'ffmpeg.exe'],
            capture_output=True,
            text=True
        )
        if "SUCCESS" in result.stdout:
            killed.append("ffmpeg")
        
        # Get all Python processes
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True
        )
        
        # Parse and kill old Python processes (not current)
        for line in result.stdout.strip().split('\n'):
            if line and 'python' in line.lower():
                try:
                    parts = line.replace('"', '').split(',')
                    if len(parts) >= 2:
                        pid = int(parts[1])
                        if pid != current_pid:
                            subprocess.run(
                                ['taskkill', '/F', '/PID', str(pid)],
                                capture_output=True
                            )
                            killed.append(f"python:{pid}")
                except (ValueError, IndexError):
                    pass
        
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    # Force garbage collection
    gc.collect()
    
    return killed


def clear_udp_sockets():
    """Clear hanging UDP sockets on common ports"""
    cleared = []
    common_ports = [5600, 5601, 5602, 1234, 2341]
    
    try:
        # Get processes using UDP ports
        result = subprocess.run(
            ['netstat', '-ano', '-p', 'UDP'],
            capture_output=True,
            text=True
        )
        
        current_pid = os.getpid()
        
        for line in result.stdout.split('\n'):
            for port in common_ports:
                if f":{port}" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            pid = int(parts[-1])
                            if pid != current_pid and pid > 0:
                                subprocess.run(
                                    ['taskkill', '/F', '/PID', str(pid)],
                                    capture_output=True
                                )
                                cleared.append(f"port:{port}:pid:{pid}")
                        except (ValueError, IndexError):
                            pass
                    break
        
    except Exception as e:
        print(f"Socket cleanup error: {e}")
    
    return cleared


def full_cleanup():
    """Perform full cleanup"""
    print("Running cleanup...")
    
    killed = kill_zombie_processes()
    cleared = clear_udp_sockets()
    
    # Force garbage collection multiple times
    for _ in range(3):
        gc.collect()
    
    total = len(killed) + len(cleared)
    if total > 0:
        print(f"Cleanup: {total} processes/sockets cleared")
        if killed:
            print(f"  Killed: {killed}")
        if cleared:
            print(f"  Cleared: {cleared}")
    else:
        print("Cleanup: Nothing to clear")
    
    return total
