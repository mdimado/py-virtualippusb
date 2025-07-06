from USBIP import *

# Interface Descriptor 1
interface1 = InterfaceDescriptor(
    bAlternateSetting=0,
    bNumEndpoints=2,
    bInterfaceClass=0x07,     # Printer class
    bInterfaceSubClass=0x01,  # Printer subclass
    bInterfaceProtocol=0x04,  # IPP-over-USB protocol
    iInterface=0
)

# Interface Descriptor 2 (identical copy for ipp-usb requirement)
interface2 = InterfaceDescriptor(
    bAlternateSetting=0,
    bNumEndpoints=2,
    bInterfaceClass=0x07,
    bInterfaceSubClass=0x01,
    bInterfaceProtocol=0x04,
    iInterface=1
)

# Endpoints
bulk_out = EndPoint(
    bEndpointAddress=0x01,  # OUT
    bmAttributes=0x02,
    wMaxPacketSize=0x0040,
    bInterval=0x00
)

bulk_in = EndPoint(
    bEndpointAddress=0x81,  # IN
    bmAttributes=0x02,
    wMaxPacketSize=0x0040,
    bInterval=0x00
)

# Bind endpoints to interfaces
interface1.descriptions = [interface1]
interface2.descriptions = [interface2]
interface1.endpoints = [bulk_out, bulk_in]
interface2.endpoints = [bulk_out, bulk_in]

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
    vendorID = 0x1234         # Dummy vendor ID (use 0x03F0 for HP)
    productID = 0x5678
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

        # Basic IPP-over-USB HTTP response (200 OK, empty body)
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 0\r\n"
            b"Content-Type: application/ipp\r\n"
            b"\r\n"
        )

        self.send_usb_req(usb_req, response, len(response))
