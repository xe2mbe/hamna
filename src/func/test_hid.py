import hid

for d in hid.enumerate():
    print(f"{d['vendor_id']:04x}:{d['product_id']:04x}  {d['manufacturer_string']} {d['product_string']}")
