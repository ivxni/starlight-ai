import hid
devs = list(hid.enumerate(0x31E3, 0x131F))
print(f"{len(devs)} bootloader device(s)")
for d in devs:
    print(f"  serial={d['serial_number']} product={d['product_string']}")
if not devs:
    print("Kein Bootloader gefunden - checking normal mode:")
    for d in hid.enumerate(0x31E3, 0x1312):
        print(f"  normal: serial={d['serial_number']} product={d['product_string']}")
