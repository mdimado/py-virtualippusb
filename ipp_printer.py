import json
import socket
import threading
import time
import requests
from urllib.parse import urlparse
from USBIP import BaseStructure, USBDevice, InterfaceDescriptor, DeviceDescriptor, DeviceConfiguration, EndpointDescriptor, USBContainer


class IPPOverUSBDevice(USBDevice):
    
    def __init__(self, config_file='ipp_usb_config.json'):
        self.config = self.load_config(config_file)
        self.server_url = self.config.get('ipp_server_url', 'http://localhost:631/ipp/print')
        self.device_name = self.config.get('device_name', 'Virtual IPP Printer')
        
        # handle hex string vendor/product ids from config
        vendor_id = self.config.get('vendor_id', '0x03F0')
        product_id = self.config.get('product_id', '0x1234')
        
        # convert hex strings to integers if needed
        if isinstance(vendor_id, str):
            self.vendor_id = int(vendor_id, 16) if vendor_id.startswith('0x') else int(vendor_id)
        else:
            self.vendor_id = vendor_id
            
        if isinstance(product_id, str):
            self.product_id = int(product_id, 16) if product_id.startswith('0x') else int(product_id)
        else:
            self.product_id = product_id
        
        self._device_descriptor = self.create_device_descriptor()
        self._configurations = self.create_configurations()
        
        super().__init__()
        
        self.tcp_connection = None
        self.tcp_connected = False
        self.connection_lock = threading.Lock()
        
        print(f"IPP over USB Proxy Device")
        print(f"Configuration: {config_file}")
        print(f"IPP Server URL: {self.server_url}")
        print(f"Device: {self.device_name}")
        print(f"Vendor ID: 0x{self.vendor_id:04X}, Product ID: 0x{self.product_id:04X}")
    
    def load_config(self, config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "ipp_server_url": "http://localhost:631/ipp/print",
                "device_name": "Virtual IPP Printer",
                "vendor_id": "0x03F0",
                "product_id": "0x1234",
                "manufacturer": "Virtual",
                "product": "IPP-USB Proxy",
                "serial": "VIP001",
                "listen_ip": "0.0.0.0",
                "listen_port": 3240,
                "debug": True
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {config_file}")
            return default_config
    
    def create_device_descriptor(self):
        return DeviceDescriptor(
            bDeviceClass=0x07,
            bDeviceSubClass=0x01,
            bDeviceProtocol=0x02,
            bMaxPacketSize0=0x40,
            idVendor=self.vendor_id,
            idProduct=self.product_id,
            bcdDevice=0x0100,
            bNumConfigurations=1
        )
    
    def create_configurations(self):
        interface_desc = InterfaceDescriptor(
            bInterfaceNumber=0,
            bAlternateSetting=0,
            bNumEndpoints=2,
            bInterfaceClass=0x07,
            bInterfaceSubClass=0x01,
            bInterfaceProtocol=0x02,
            iInterface=0
        )
        
        bulk_out_endpoint = EndpointDescriptor(
            bEndpointAddress=0x01,
            bmAttributes=0x02,
            wMaxPacketSize=0x0200,
            bInterval=0x00
        )
        
        bulk_in_endpoint = EndpointDescriptor(
            bEndpointAddress=0x82,
            bmAttributes=0x02,
            wMaxPacketSize=0x0200,
            bInterval=0x00
        )
        
        interface_desc.endpoints = [bulk_out_endpoint, bulk_in_endpoint]
        interface = [interface_desc]
        
        config = DeviceConfiguration(
            wTotalLength=0x0020,
            bNumInterfaces=1,
            bConfigurationValue=1,
            iConfiguration=0,
            bmAttributes=0xC0,
            bMaxPower=0x32
        )
        
        config.interfaces = [interface]
        return [config]
    
    @property
    def device_descriptor(self):
        return self._device_descriptor
    
    @property
    def configurations(self):
        return self._configurations
    
    def connect_to_server(self):
        try:
            parsed_url = urlparse(self.server_url)
            host = parsed_url.hostname or 'localhost'
            port = parsed_url.port or 631
            
            print(f"Connecting to IPP server at {host}:{port}")
            
            with self.connection_lock:
                if self.tcp_connection:
                    try:
                        self.tcp_connection.close()
                    except:
                        pass
                
                self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_connection.settimeout(10.0)
                self.tcp_connection.connect((host, port))
                self.tcp_connected = True
                
            print("Successfully connected to IPP server")
            return True
            
        except Exception as e:
            print(f"Failed to connect to IPP server: {e}")
            with self.connection_lock:
                self.tcp_connected = False
                if self.tcp_connection:
                    try:
                        self.tcp_connection.close()
                    except:
                        pass
                    self.tcp_connection = None
            return False
    
    def disconnect_from_server(self):
        with self.connection_lock:
            if self.tcp_connection:
                try:
                    self.tcp_connection.close()
                except:
                    pass
                self.tcp_connection = None
            self.tcp_connected = False
    
    def handle_data(self, usb_req):
        if usb_req.ep == 0x01:
            self.handle_bulk_out(usb_req)
        elif usb_req.ep == 0x82:
            self.handle_bulk_in(usb_req)
        else:
            print(f"Unknown endpoint: {usb_req.ep:02x}")
            self.send_usb_ret(usb_req, b'', 0, status=1)
    
    def handle_bulk_out(self, usb_req):
        try:
            if not usb_req.transfer_buffer:
                self.send_usb_ret(usb_req, b'', 0)
                return
            
            print(f"Received {len(usb_req.transfer_buffer)} bytes from host")
            
            if not self.tcp_connected:
                if not self.connect_to_server():
                    self.send_usb_ret(usb_req, b'', 0, status=1)
                    return
            
            try:
                with self.connection_lock:
                    if self.tcp_connection and self.tcp_connected:
                        self.tcp_connection.send(usb_req.transfer_buffer)
                        print(f"Forwarded {len(usb_req.transfer_buffer)} bytes to IPP server")
                        
                        self.tcp_connection.settimeout(0.1)
                        try:
                            response = self.tcp_connection.recv(8192)
                            if response:
                                print(f"Received immediate response: {len(response)} bytes")
                                if not hasattr(self, 'pending_response'):
                                    self.pending_response = bytearray()
                                self.pending_response.extend(response)
                        except socket.timeout:
                            pass
                        finally:
                            self.tcp_connection.settimeout(10.0)
                        
                        self.send_usb_ret(usb_req, b'', len(usb_req.transfer_buffer))
                    else:
                        self.send_usb_ret(usb_req, b'', 0, status=1)
                        
            except Exception as e:
                print(f"Error forwarding to IPP server: {e}")
                self.disconnect_from_server()
                self.send_usb_ret(usb_req, b'', 0, status=1)
                
        except Exception as e:
            print(f"Error in bulk_out handler: {e}")
            self.send_usb_ret(usb_req, b'', 0, status=1)
    
    def handle_bulk_in(self, usb_req):
        try:
            if hasattr(self, 'pending_response') and self.pending_response:
                data_to_send = bytes(self.pending_response[:usb_req.transfer_buffer_length])
                self.pending_response = self.pending_response[len(data_to_send):]
                
                if not self.pending_response:
                    delattr(self, 'pending_response')
                
                print(f"Sending {len(data_to_send)} bytes to host from buffer")
                self.send_usb_ret(usb_req, data_to_send, len(data_to_send))
                return
            
            if not self.tcp_connected:
                self.send_usb_ret(usb_req, b'', 0)
                return
            
            try:
                with self.connection_lock:
                    if self.tcp_connection and self.tcp_connected:
                        self.tcp_connection.settimeout(0.1)
                        try:
                            response = self.tcp_connection.recv(usb_req.transfer_buffer_length)
                            if response:
                                print(f"Received {len(response)} bytes from IPP server")
                                self.send_usb_ret(usb_req, response, len(response))
                            else:
                                self.send_usb_ret(usb_req, b'', 0)
                        except socket.timeout:
                            self.send_usb_ret(usb_req, b'', 0)
                        finally:
                            self.tcp_connection.settimeout(10.0)
                    else:
                        self.send_usb_ret(usb_req, b'', 0)
                        
            except Exception as e:
                print(f"Error reading from IPP server: {e}")
                self.disconnect_from_server()
                self.send_usb_ret(usb_req, b'', 0)
                
        except Exception as e:
            print(f"Error in bulk_in handler: {e}")
            self.send_usb_ret(usb_req, b'', 0, status=1)
    
    def handle_device_specific_control(self, control_req, usb_req):
        if control_req.bmRequestType == 0xA1:
            if control_req.bRequest == 0x01:
                device_id = f'MFG:{self.config.get("manufacturer", "Virtual")};' \
                           f'CMD:PostScript,PDF;' \
                           f'MDL:{self.config.get("product", "IPP-USB Proxy")};' \
                           f'CLS:PRINTER;'
                
                device_id_bytes = device_id.encode('ascii')
                length_bytes = len(device_id_bytes).to_bytes(2, byteorder='big')
                response = length_bytes + device_id_bytes
                
                self.send_usb_ret(usb_req, response, len(response))
                return
            
            elif control_req.bRequest == 0x02:
                status = 0x18
                self.send_usb_ret(usb_req, status.to_bytes(1, byteorder='little'), 1)
                return
        
        elif control_req.bmRequestType == 0x21:
            if control_req.bRequest == 0x02:
                print("Printer soft reset requested")
                self.send_usb_ret(usb_req, b'', 0)
                return
        
        print(f"Unhandled control request: {control_req.bmRequestType:02x} {control_req.bRequest:02x}")
        self.send_usb_ret(usb_req, b'', 0, status=1)


def main():
    try:
        ipp_device = IPPOverUSBDevice()
        
        usb_container = USBContainer()
        usb_container.add_usb_device(ipp_device)
        
        # get listen settings from config
        listen_ip = ipp_device.config.get('listen_ip', '0.0.0.0')
        listen_port = ipp_device.config.get('listen_port', 3240)
        
        print(f"Listening on {listen_ip}:{listen_port}")
        print("Press Ctrl+C to stop")
        
        usb_container.run(ip=listen_ip, port=listen_port)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'ipp_device' in locals():
            ipp_device.disconnect_from_server()


if __name__ == "__main__":
    main()