# IPP-over-USB Virtual Device

## Architecture

```
[IPP Client] → [ipp-usb daemon] → [Virtual USB Device] → [IPP Server/CUPS]
```

## Configuration

Edit `ipp_usb_config.json` to customize the virtual device:

```json
{
  "ipp_server_url": "http://localhost:631/ipp/print",
  "device_name": "Virtual USB-IPP-Proxy",
  "vendor_id": "0x03F0",
  "product_id": "0x1234",
  "manufacturer": "Virtual",
  "product": "IPP-USB Proxy",
  "serial": "VIP001",
  "listen_ip": "0.0.0.0",
  "listen_port": 3240,
  "debug": true
}
```

### Configuration Options

- `ipp_server_url`: Target IPP server (current: CUPS on port 631)
- `device_name`: Display name for the virtual printer
- `vendor_id`/`product_id`: USB identifiers (hex format)
- `manufacturer`/`product`/`serial`: Device identification strings
- `listen_ip`/`listen_port`: USB/IP server binding
- `debug`: Enable verbose logging

## Usage

### Basic Operation

1. **Start the virtual device:**
```bash
python3 ipp_printer.py
```

2. **In another terminal, attach the virtual device:**
```bash
sudo usbip attach -r localhost -b 1-1
```

3. **Verify the device is recognized:**
```bash
lsusb
# Should show your virtual printer
```

4. **Check if ipp-usb daemon detects it:**
```bash
sudo systemctl status ipp-usb
# or
sudo ipp-usb check
```
