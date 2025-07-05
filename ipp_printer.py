from USBIP import *  
  
# Define printer configuration structures  
interface_d = InterfaceDescriptor(  
    bAlternateSetting=0,  
    bNumEndpoints=2,  # Bulk IN and OUT endpoints  
    bInterfaceClass=7,  # Printer class  
    bInterfaceSubClass=1,  # Printer subclass  
    bInterfaceProtocol=2,  # Bidirectional protocol  
    iInterface=0  
)  
  
# Bulk OUT endpoint (computer -> printer)  
bulk_out = EndPoint(  
    bEndpointAddress=0x01,  # OUT endpoint  
    bmAttributes=0x02,  # Bulk transfer  
    wMaxPacketSize=0x0040,  # 64 bytes  
    bInterval=0x00  
)  
  
# Bulk IN endpoint (printer -> computer)    
bulk_in = EndPoint(  
    bEndpointAddress=0x81,  # IN endpoint  
    bmAttributes=0x02,  # Bulk transfer  
    wMaxPacketSize=0x0040,  # 64 bytes  
    bInterval=0x00  
)  
  
configuration = DeviceConfigurations(  
    wTotalLength=0x2000,  # Will be calculated  
    bNumInterfaces=0x1,  
    bConfigurationValue=0x1,  
    iConfiguration=0x0,  
    bmAttributes=0x80,  # Bus powered  
    bMaxPower=50  # 100mA  
)  
  
interface_d.descriptions = [interface_d]  # Minimal
interface_d.endpoints = [bulk_out, bulk_in]  
configuration.interfaces = [interface_d]  
  
class USBIPPPrinter(USBDevice):  
    vendorID = 0x03F0  
    productID = 0x1234  
    bDeviceClass = 0x07    # USB Printer class  s
    bDeviceSubClass = 0x01 # Printer subclass    
    bDeviceProtocol = 0x02 # Bidirectional protocol  
    bNumConfigurations = 1  
    bConfigurationValue = 1
    bNumInterfaces = 1  
    configurations = [configuration]  # This was missing!  
      
    def handle_data(self, usb_req):  
        print("Received IPP data on endpoint:", usb_req.ep)  
        self.send_usb_req(usb_req, "IPP/1.1 200 OK\r\n", 16)