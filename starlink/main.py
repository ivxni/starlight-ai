"""
Starlink v2.0 - Test & Debug Tool
"""

import sys
import time
import argparse


def main():
    from src.controller import (
        ArduinoMouseController, 
        find_arduino_port, 
        list_serial_ports
    )
    
    parser = argparse.ArgumentParser(description="Starlink Mouse Controller Test")
    parser.add_argument("--port", "-p", help="Serial port (auto-detect if not specified)")
    parser.add_argument("--list", "-l", action="store_true", help="List available ports")
    parser.add_argument("--test", "-t", action="store_true", help="Run movement test")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--benchmark", "-b", action="store_true", help="Latency benchmark")
    args = parser.parse_args()
    
    # List ports
    if args.list:
        print("\n=== Available Serial Ports ===\n")
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found")
        else:
            for p in ports:
                print(f"  Port: {p['port']}")
                print(f"    Description: {p['description']}")
                print(f"    VID:PID: {p['vid']}:{p['pid']}")
                print(f"    Manufacturer: {p['manufacturer']}")
                print()
        
        # Try auto-detect
        auto_port = find_arduino_port()
        if auto_port:
            print(f"Auto-detected Arduino: {auto_port}")
        else:
            print("No Arduino auto-detected")
        return
    
    # Connect
    print("\n=== Starlink v2.0 ===\n")
    
    mouse = ArduinoMouseController(port=args.port)
    if not mouse.connect():
        print("Failed to connect. Use --list to see available ports.")
        return 1
    
    # Get info
    version = mouse.get_version()
    print(f"Firmware version: {version}")
    
    status = mouse.get_status()
    if status:
        print(f"Status: {status}")
    
    # Benchmark mode
    if args.benchmark:
        print("\n=== Latency Benchmark ===\n")
        latencies = []
        
        for i in range(100):
            start = time.perf_counter()
            mouse._send_command("?")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/100...")
        
        avg = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        
        print(f"\nResults (100 pings):")
        print(f"  Average: {avg:.2f} ms")
        print(f"  Min: {min_lat:.2f} ms")
        print(f"  Max: {max_lat:.2f} ms")
        
        mouse.disconnect()
        return
    
    # Test mode
    if args.test:
        print("\n=== Movement Test ===\n")
        print("Testing humanization layers...")
        print("Watch your mouse cursor!\n")
        
        time.sleep(1)
        
        # Test 1: Slow precise movement
        print("1. Slow movement (low jitter)...")
        mouse.set_humanization(enabled=True, jitter=30, tremor=30)
        for _ in range(20):
            mouse.move(2, 0)
            time.sleep(0.02)
        time.sleep(0.5)
        
        # Test 2: Fast movement
        print("2. Fast movement (higher jitter)...")
        for _ in range(10):
            mouse.move(15, 10)
            time.sleep(0.01)
        time.sleep(0.5)
        
        # Test 3: Smooth movement
        print("3. Smooth diagonal...")
        mouse.move_smooth(100, 100, steps=20, interval_ms=5)
        time.sleep(0.5)
        
        # Test 4: Back to start
        print("4. Return movement...")
        mouse.move_smooth(-100, -100, steps=20, interval_ms=5)
        time.sleep(0.5)
        
        # Test 5: Circle pattern
        print("5. Circle pattern...")
        import math
        for i in range(60):
            angle = (i / 60) * 2 * math.pi
            dx = math.cos(angle) * 3
            dy = math.sin(angle) * 3
            mouse.move(dx, dy)
            time.sleep(0.016)
        
        print("\nTest complete!")
        print(f"Total moves sent: {mouse.moves_sent}")
        
        mouse.disconnect()
        return
    
    # Interactive mode
    if args.interactive:
        print("\n=== Interactive Mode ===\n")
        print("Commands:")
        print("  m <dx> <dy>  - Move mouse")
        print("  c [L/R/M]    - Click button")
        print("  j <0-100>    - Set jitter")
        print("  t <0-100>    - Set tremor")
        print("  h <0/1>      - Humanization on/off")
        print("  s            - Status")
        print("  q            - Quit")
        print()
        
        try:
            while True:
                cmd = input("> ").strip().lower()
                
                if not cmd:
                    continue
                
                parts = cmd.split()
                action = parts[0]
                
                if action == "q":
                    break
                
                elif action == "m" and len(parts) >= 3:
                    dx = float(parts[1])
                    dy = float(parts[2])
                    mouse.move(dx, dy)
                    print(f"Moved: {dx}, {dy}")
                
                elif action == "c":
                    btn = parts[1].upper() if len(parts) > 1 else "L"
                    mouse.click(btn)
                    print(f"Clicked: {btn}")
                
                elif action == "j" and len(parts) >= 2:
                    val = int(parts[1])
                    mouse.set_jitter(val)
                    print(f"Jitter: {val}")
                
                elif action == "t" and len(parts) >= 2:
                    val = int(parts[1])
                    mouse.set_tremor(val)
                    print(f"Tremor: {val}")
                
                elif action == "h" and len(parts) >= 2:
                    enabled = parts[1] == "1"
                    mouse.enable_humanization(enabled)
                    print(f"Humanization: {'ON' if enabled else 'OFF'}")
                
                elif action == "s":
                    status = mouse.get_status()
                    print(f"Status: {status}")
                    print(f"Latency: {mouse.last_latency_ms:.2f} ms")
                
                else:
                    print("Unknown command")
        
        except KeyboardInterrupt:
            print("\nInterrupted")
        
        mouse.disconnect()
        return
    
    # Default: quick test
    print("\nQuick test - moving cursor right...")
    mouse.move(50, 0)
    time.sleep(0.1)
    print("Done!")
    print(f"\nUse --test for full test, --interactive for manual control")
    
    mouse.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
