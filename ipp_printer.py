from USBIP import *

# Interface Descriptor 1
interface1 = InterfaceDescriptor(
    bInterfaceNumber=0,
    bAlternateSetting=0,
    bNumEndpoints=2,
    bInterfaceClass=0x07,     # Printer class
    bInterfaceSubClass=0x01,  # Printer subclass
    bInterfaceProtocol=0x04,  # IPP-over-USB protocol
    iInterface=0
)

# Interface Descriptor 2
interface2 = InterfaceDescriptor(
    bInterfaceNumber=1,
    bAlternateSetting=0,
    bNumEndpoints=2,
    bInterfaceClass=0x07,
    bInterfaceSubClass=0x01,
    bInterfaceProtocol=0x04,
    iInterface=1
)

# Endpoints for interface 1
bulk_out_1 = EndPoint(
    bEndpointAddress=0x01,  # OUT
    bmAttributes=0x02,      # Bulk
    wMaxPacketSize=0x0040,
    bInterval=0x00
)

bulk_in_1 = EndPoint(
    bEndpointAddress=0x81,  # IN
    bmAttributes=0x02,      # Bulk
    wMaxPacketSize=0x0040,
    bInterval=0x00
)

# Endpoints for interface 2
bulk_out_2 = EndPoint(
    bEndpointAddress=0x02,  # OUT
    bmAttributes=0x02,      # Bulk
    wMaxPacketSize=0x0040,
    bInterval=0x00
)

bulk_in_2 = EndPoint(
    bEndpointAddress=0x82,  # IN
    bmAttributes=0x02,      # Bulk
    wMaxPacketSize=0x0040,
    bInterval=0x00
)

# Bind endpoints to interfaces
interface1.descriptions = []  # Empty - no additional descriptors
interface2.descriptions = []  # Empty - no additional descriptors
interface1.endpoints = [bulk_out_1, bulk_in_1]
interface2.endpoints = [bulk_out_2, bulk_in_2]

# Device Configuration
configuration = DeviceConfigurations(
    wTotalLength=0x2000,
    bNumInterfaces=2,
    bConfigurationValue=1,
    iConfiguration=0,
    bmAttributes=0x80,  # Bus powered
    bMaxPower=50        # 100 mA
)

configuration.interfaces = [interface1, interface2]

# Virtual IPP-over-USB printer device
class USBIPPPrinter(USBDevice):
    vendorID = 0x03F0         # HP vendor ID
    productID = 0x1234        # Dummy product ID
    bcdDevice = 0x0100
    bDeviceClass = 0x00       # Interface-specified
    bDeviceSubClass = 0x00
    bDeviceProtocol = 0x00
    bNumConfigurations = 1
    bConfigurationValue = 1
    bNumInterfaces = 2
    configurations = [configuration]

    def __init__(self):
        super().__init__()
        print("[USBIPPPrinter] Initialized virtual IPP-over-USB printer")

    def handle_data(self, usb_req):
        print(f"[USBIPPPrinter] Received data on endpoint {usb_req.ep}")
        
        if hasattr(usb_req, 'data') and usb_req.data:
            print(f"[USBIPPPrinter] Data received: {usb_req.data[:100]}...")  # Print first 100 bytes
        
        # Basic IPP-over-USB HTTP response (200 OK, empty body)
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 0\r\n"
            b"Content-Type: application/ipp\r\n"
            b"\r\n"
        )

        self.send_usb_req(usb_req, response, len(response))

    def handle_unknown_control(self, control_req, usb_req):
        """Handle unknown control requests"""
        print(f"[USBIPPPrinter] Unknown control request: {control_req.bmRequestType:02x} {control_req.bRequest:02x}")
        # Send empty response with status 0 (success)
        self.send_usb_req(usb_req, b'', 0, 0)