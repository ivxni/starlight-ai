"""Check what serial is in the patched firmware."""
import re

path = r"C:\Users\angel\Desktop\starlight-ai\startility\wooting_60he_arm_patched.fwr"

with open(path, 'r') as f:
    content = f.read()

lines = content.strip().split('\n')
print(f"Patched firmware: {len(lines)} lines")

# Parse all data bytes
data = bytearray()
base = 0
records = []

for line in lines:
    line = line.strip()
    if not line.startswith(':'): continue
    raw = bytes.fromhex(line[1:])
    bc = raw[0]
    addr = (raw[1] << 8) | raw[2]
    rtype = raw[3]
    payload = raw[4:4+bc]
    
    if rtype == 4:
        base = ((raw[4] << 8) | raw[5]) << 16
    elif rtype == 0:
        abs_addr = base + addr
        records.append((abs_addr, payload))

if not records:
    print("No data records!")
    exit()

min_addr = min(a for a, _ in records)
max_end = max(a + len(d) for a, d in records)
data = bytearray(b'\xff' * (max_end - min_addr))
for addr, payload in records:
    data[addr - min_addr:addr - min_addr + len(payload)] = payload

print(f"Address range: 0x{min_addr:08X} - 0x{max_end:08X}")
print(f"Binary size: {len(data)} bytes")

# Search for serial-like strings  
text = data.decode('ascii', errors='ignore')

# Look for A0 serial patterns
serials = re.findall(r'A0[0-9][A-Z][0-9]{4}W[0-9]{3}H[0-9]{5}', text)
print(f"\nSerial patterns (A0x format): {serials}")

# Look for format strings
for pat in ['%c%d%c%d', '%02d%c%04d%c', 'A03B', 'A02B', 'serial', 'Serial']:
    idx = 0
    while True:
        idx = text.find(pat, idx)
        if idx < 0: break
        ctx = text[max(0,idx-5):idx+35]
        print(f"Found '{pat}' at offset 0x{idx:X}: {repr(ctx)}")
        idx += 1

# Also check for the original format string vs hardcoded
# The patcher should have replaced the format string with a hardcoded serial
for pat in [b'%c%02d%c%04d%c%03d%c%05d', b'A03B2519W041H28437']:
    idx = data.find(pat)
    if idx >= 0:
        ctx = data[idx:idx+30]
        print(f"Found {pat[:20]} at binary offset 0x{idx:X}: {ctx}")
    else:
        print(f"NOT found: {pat[:30]}")
