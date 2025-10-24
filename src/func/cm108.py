import hid   # usa el paquete correcto


# HID helpers
def hid_enumerate_filtered():
    devices = []
    labels = []
    for d in hid.enumerate():
        man = (d.get("manufacturer_string") or "")
        prod = (d.get("product_string") or "")
        vid = d.get("vendor_id")
        pid = d.get("product_id")
        if vid == 0x0D8C or "C-Media" in man or "C-Media" in prod or "USB Audio" in prod:
            devices.append(d)
            labels.append(f"{vid:04x}:{pid:04x}  {man} {prod}".strip())
    return devices, labels

def hid_open_device(d):
    dev = hid.device()
    path = d.get("path")
    if path:
        dev.open_path(path)
    else:
        dev.open(d.get("vendor_id"), d.get("product_id"))
    try:
        dev.set_nonblocking(True)
    except Exception:
        pass
    return dev

def hid_close_device(dev):
    try:
        dev.close()
    except Exception:
        pass

def hid_set_ptt(dev, ptt_bit: int, state: bool, invert: bool = False):
    if not dev:
        return False
    out_state = state if not invert else (not state)
    buf = bytes([0x00, ptt_bit if out_state else 0x00, 0x00, 0x00])
    try:
        dev.send_feature_report(buf)
        return True
    except Exception:
        try:
            dev.set_output_report(0x00, buf)
            return True
        except Exception:
            dev.write(buf)
            return True

def hid_read_cos(dev, cos_bit: int, invert: bool = True):
    if not dev:
        return None
    data = None
    try:
        data = dev.read(8, 50)
    except Exception:
        data = None
    if not data:
        try:
            data = dev.get_input_report(0x01, 4)
        except Exception:
            data = None
    if not data:
        return None
    try:
        b1 = data[1] if len(data) > 1 else 0
    except Exception:
        b1 = 0
    measured = bool(b1 & cos_bit)
    return (not measured) if invert else measured

