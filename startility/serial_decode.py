"""
Startility - Wooting Serial Number Decoder
===========================================
Decodes the raw bytes from GET_SERIAL response into human-readable format.

Serial format: A02B2247W052H16911
Protobuf SerialNumber fields:
  1: SupplierNumber (uint32)
  2: Year (uint32)  
  3: WeekNumber (uint32)
  4: ProductNumber (uint32)
  5: RevisionNumber (uint32)
  6: ProductId (uint32)
  7: Stage (enum ProductionStage)
  9: Variant (uint32)
"""

import struct


def decode_serial_response(raw_hex):
    """Decode the raw response from GET_SERIAL command.
    
    Response format: [Report ID 01] [D1DA] [CMD 03] [88] [size] [00] [protobuf_data]
    """
    if isinstance(raw_hex, str):
        data = bytes.fromhex(raw_hex.replace(" ", ""))
    else:
        data = raw_hex
    
    # Strip Report ID + D1DA + CMD + header
    # Full response: 01 d1da 03 88 0b 00 [payload]
    # Find the D1DA marker
    idx = data.find(b"\xd1\xda")
    if idx < 0:
        print("[-] D1DA marker not found in response")
        return None
    
    # Skip D1DA (2) + CMD (1) + header byte (1)
    after_header = data[idx + 4:]
    
    # First byte should be payload length
    if len(after_header) < 2:
        print("[-] Response too short")
        return None
    
    payload_len = after_header[0]
    # Skip length byte + padding byte (00)
    payload = after_header[2:2 + payload_len]
    
    print(f"[+] Payload ({payload_len} bytes): {payload.hex()}")
    
    # Try to decode as protobuf
    result = decode_protobuf_serial(payload)
    return result


def decode_varint(data, offset):
    """Decode a protobuf varint."""
    result = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        result |= (b & 0x7F) << shift
        offset += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, offset


def decode_protobuf_serial(payload):
    """Attempt to decode protobuf-encoded SerialNumber message."""
    print("\n[*] Attempting protobuf decode...")
    
    fields = {}
    offset = 0
    while offset < len(payload):
        if payload[offset] == 0:
            offset += 1
            continue
        
        key, offset = decode_varint(payload, offset)
        field_num = key >> 3
        wire_type = key & 0x07
        
        if wire_type == 0:  # Varint
            value, offset = decode_varint(payload, offset)
            fields[field_num] = value
            print(f"    Field {field_num}: {value} (0x{value:X})")
        elif wire_type == 2:  # Length-delimited
            length, offset = decode_varint(payload, offset)
            value = payload[offset:offset + length]
            offset += length
            fields[field_num] = value
            print(f"    Field {field_num}: {value.hex()} (bytes, len={length})")
        else:
            print(f"    Field {field_num}: wire_type={wire_type} (skipping)")
            break
    
    return fields


def try_direct_binary_decode(payload):
    """Try decoding as a simple binary struct instead of protobuf."""
    print("\n[*] Attempting direct binary decode...")
    print(f"    Raw: {payload.hex()}")
    
    # Known mappings from serial A02B2247W052H16911:
    # Year=22=0x16, Week=47=0x2F, ProductNumber=16911=0x420F
    
    # Try various struct layouts
    layouts = [
        ("HHBBHH", "supplier(u16) unknown(u16) year(u8) week(u8) prodnum(u16) rest(u16)"),
        ("HBBHHHB", "supplier(u16) year(u8) week(u8) a(u16) b(u16) c(u16) d(u8)"),
    ]
    
    for fmt, desc in layouts:
        try:
            size = struct.calcsize("<" + fmt)
            if size <= len(payload):
                values = struct.unpack("<" + fmt, payload[:size])
                print(f"    Layout '{desc}': {values}")
        except:
            pass


# ── Known serial: A02B2247W052H16911 ────────────────────────────
# Response payload: 02 00 16 2F 05 00 02 00 0F 42 00

KNOWN_SERIAL = "A02B2247W052H16911"
KNOWN_RESPONSE = "01d1da03880b000200162f050002000f4200000000000000000000000000000000"


if __name__ == "__main__":
    print("=" * 60)
    print("  Startility - Serial Number Decoder")
    print("=" * 60)
    print()
    
    print(f"[*] Known USB serial: {KNOWN_SERIAL}")
    print(f"[*] Known response:   {KNOWN_RESPONSE}")
    print()
    
    result = decode_serial_response(KNOWN_RESPONSE)
    
    # Also try direct binary
    payload = bytes.fromhex("0200162f050002000f4200")
    try_direct_binary_decode(payload)
    
    print()
    print("=" * 60)
    print("[*] Analysis Summary:")
    print("=" * 60)
    print()
    print(f"Serial: {KNOWN_SERIAL}")
    print()
    print("  Binary layout (Little-Endian):")
    print("  Offset 0-1: uint16 = 2      -> SupplierNumber")
    print("  Offset 2:   uint8  = 22     -> Year (2022)")
    print("  Offset 3:   uint8  = 47     -> WeekNumber")  
    print("  Offset 4-5: uint16 = 5      -> RevisionNumber")
    print("  Offset 6-7: uint16 = 2      -> ProductId")
    print("  Offset 8-9: uint16 = 16911  -> ProductNumber")
    print("  Offset 10:  uint8  = 0      -> Stage")
    print()
    print("  Serial string mapping:")
    print("    A      = Stage (0=A)")
    print("    02     = SupplierNumber (2, zero-padded)")
    print("    B      = ProductId letter (2->B)")
    print("    2247   = Year+Week (22, 47)")
    print("    W052   = W + RevisionNumber (5, zero-padded)")
    print("    H16911 = H + ProductNumber (16911)")
