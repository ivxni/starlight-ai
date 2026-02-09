import hid
devs = hid.enumerate(0x31E3, 0x1312)
print(f"Found {len(devs)} interfaces")
for d in devs[:5]:
    print(f"  serial={d['serial_number']}, usage=0x{d['usage_page']:X}, product={d['product_string']}")
