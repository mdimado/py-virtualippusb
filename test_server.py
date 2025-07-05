from ipp_printer import USBIPPPrinter
from USBIP import USBContainer

if __name__ == "__main__":
    printer = USBIPPPrinter()
    container = USBContainer()
    container.add_usb_device(printer)
    print("Starting IPP-over-USB server on port 3240...")
    container.run()