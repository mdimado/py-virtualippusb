import socket
import struct
import types
import time

class BaseStucture:
    def __init__(self, **kwargs):
        self.init_from_dict(**kwargs)
        for field in self._fields_:
            if len(field) > 2:
                if not hasattr(self, field[0]):
                    setattr(self, field[0], field[2])

    def init_from_dict(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def size(self):
        return struct.calcsize(self.format())

    def format(self):
        pack_format = '>'
        for field in self._fields_:
            if hasattr(field[1], '__class__') and hasattr(field[1], '__bases__'):
                if BaseStucture in field[1].__class__.__bases__:
                    pack_format += str(field[1].size()) + 's'
            elif isinstance(field[1], str):
                if 'si' == field[1]:
                    pack_format += 'c'
                elif '<' in field[1]:
                    pack_format += field[1][1:]
                else:
                    pack_format += field[1]
            else:
                # Handle non-string field types (like nested objects)
                if hasattr(field[1], 'size'):
                    pack_format += str(field[1].size()) + 's'
        return pack_format

    def pack(self):
        values = []
        for field in self._fields_:
            if hasattr(field[1], '__class__') and hasattr(field[1], '__bases__'):
                if BaseStucture in field[1].__class__.__bases__:
                     values.append(getattr(self, field[0], 0).pack())
            elif isinstance(field[1], str):
                if 'si' == field[1]:
                    values.append(bytes([getattr(self, field[0], 0)]))
                else:
                    values.append(getattr(self, field[0], 0))
            else:
                # Handle non-string field types (like nested objects)
                if hasattr(field[1], 'pack'):
                    values.append(getattr(self, field[0], field[1]).pack())
                else:
                    values.append(getattr(self, field[0], 0))
        return struct.pack(self.format(), *values)

    def unpack(self, buf):
        values = struct.unpack(self.format(), buf)
        i = 0
        keys_vals = {}
        for val in values:
            if isinstance(self._fields_[i][1], str) and '<' in self._fields_[i][1] and len(self._fields_[i][1]) > 1:
                val = struct.unpack('<' + self._fields_[i][1][1], struct.pack('>' + self._fields_[i][1][1], val))[0]
            keys_vals[self._fields_[i][0]] = val
            i += 1

        self.init_from_dict(**keys_vals)


def int_to_hex_string(val):
    sval = format(val, 'x')
    if len(sval) < 16:
        for i in range(len(sval), 16):
            sval = '0' + sval
    return bytes.fromhex(sval)


class USBIPHeader(BaseStucture):
    _fields_ = [
        ('version', 'H', 0x0111),  # Version 1.1.1
        ('command', 'H'),
        ('status', 'I')
    ]


class USBInterface(BaseStucture):
    _fields_ = [
        ('bInterfaceClass', 'B'),
        ('bInterfaceSubClass', 'B'),
        ('bInterfaceProtocol', 'B'),
        ('align', 'B', 0)
    ]


class OPREPDevList(BaseStucture):
    _fields_ = [
        ('base', USBIPHeader()),
        ('nExportedDevice', 'I'),
        ('usbPath', '256s'),
        ('busID', '32s'),
        ('busnum', 'I'),
        ('devnum', 'I'),
        ('speed', 'I'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bConfigurationValue', 'B'),
        ('bNumConfigurations', 'B'),
        ('bNumInterfaces', 'B')
    ]

    def pack(self):
        """Custom pack method to handle multiple interfaces"""
        # Pack the base structure first
        base_packed = BaseStucture.pack(self)
        
        # Add interface data for each interface
        if hasattr(self, 'interfaces') and self.interfaces:
            for interface in self.interfaces:
                base_packed += interface.pack()
        
        return base_packed


class OPREPImport(BaseStucture):
    _fields_ = [
        ('base', USBIPHeader()),
        ('usbPath', '256s'),
        ('busID', '32s'),
        ('busnum', 'I'),
        ('devnum', 'I'),
        ('speed', 'I'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bConfigurationValue', 'B'),
        ('bNumConfigurations', 'B'),
        ('bNumInterfaces', 'B')
    ]


class USBIPRETSubmit(BaseStucture):
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),
        ('status', 'I'),
        ('actual_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('error_count', 'I'),
        ('setup', 'Q')
    ]

    def pack(self):
        packed_data = BaseStucture.pack(self)
        if hasattr(self, 'data'):
            packed_data += self.data
        return packed_data


class USBIPCMDSubmit(BaseStucture):
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),
        ('transfer_flags', 'I'),
        ('transfer_buffer_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('interval', 'I'),
        ('setup', 'Q')
    ]


class USBIPUnlinkReq(BaseStucture):
    _fields_ = [
        ('command', 'I', 0x2),
        ('seqnum', 'I'),
        ('devid', 'I', 0x2),
        ('direction', 'I'),
        ('ep', 'I'),
        ('transfer_flags', 'I'),
        ('transfer_buffer_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('interval', 'I'),
        ('setup', 'Q')
    ]


class StandardDeviceRequest(BaseStucture):
    _fields_ = [
        ('bmRequestType', 'B'),
        ('bRequest', 'B'),
        ('wValue', 'H'),
        ('wIndex', 'H'),
        ('wLength', '<H')
    ]


class DeviceDescriptor(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 18),
        ('bDescriptorType', 'B', 1),
        ('bcdUSB', 'H', 0x0200),  # USB 2.0
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bMaxPacketSize0', 'B', 64),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('iManufacturer', 'B'),
        ('iProduct', 'B'),
        ('iSerialNumber', 'B'),
        ('bNumConfigurations', 'B')
    ]


class DeviceConfigurations(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 2),
        ('wTotalLength', 'H', 0x2200),
        ('bNumInterfaces', 'B', 1),
        ('bConfigurationValue', 'B', 1),
        ('iConfiguration', 'B', 0),
        ('bmAttributes', 'B', 0x80),
        ('bMaxPower', 'B', 0x32)
    ]


class InterfaceDescriptor(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 4),
        ('bInterfaceNumber', 'B', 0),
        ('bAlternateSetting', 'B', 0),
        ('bNumEndpoints', 'B', 1),
        ('bInterfaceClass', 'B', 3),
        ('bInterfaceSubClass', 'B', 1),
        ('bInterfaceProtocol', 'B', 2),
        ('iInterface', 'B', 0)
    ]


class EndPoint(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 7),
        ('bDescriptorType', 'B', 0x5),
        ('bEndpointAddress', 'B', 0x81),
        ('bmAttributes', 'B', 0x3),
        ('wMaxPacketSize', 'H', 0x0040),  # 64 bytes
        ('bInterval', 'B', 0x0A)
    ]


class USBRequest():
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class USBDevice():
    def __init__(self):
        self.generate_raw_configuration()

    def generate_raw_configuration(self):
        config_str = self.configurations[0].pack()
        
        # Handle multiple interfaces properly
        for interface in self.configurations[0].interfaces:
            config_str += interface.pack()
            
            # Add interface descriptors
            for desc in interface.descriptions:
                config_str += desc.pack()
            
            # Add endpoint descriptors
            for endpoint in interface.endpoints:
                config_str += endpoint.pack()
        
        self.all_configurations = config_str

    def send_usb_req(self, usb_req, usb_res, usb_len, status=0):
        response = USBIPRETSubmit(command=0x3,
                                  seqnum=usb_req.seqnum,
                                  devid=0,  # Server should set this to 0
                                  direction=0,  # Server should set this to 0
                                  ep=0,
                                  status=status,
                                  actual_length=usb_len,
                                  start_frame=0x0,
                                  number_of_packets=0xffffffff,
                                  error_count=0,
                                  setup=0,
                                  data=usb_res)
        try:
            self.connection.sendall(response.pack())
            print(f"[USB] Sent response: {len(response.pack())} bytes, status={status}")
        except Exception as e:
            print(f"[USB] Error sending response: {e}")

    def handle_get_descriptor(self, control_req, usb_req):
        handled = False
        print("handle_get_descriptor {}".format(control_req.wValue))
        if control_req.wValue == 0x0100:  # Device descriptor
            handled = True
            ret = DeviceDescriptor(bDeviceClass=self.bDeviceClass,
                                   bDeviceSubClass=self.bDeviceSubClass,
                                   bDeviceProtocol=self.bDeviceProtocol,
                                   bMaxPacketSize0=64,
                                   idVendor=self.vendorID,
                                   idProduct=self.productID,
                                   bcdDevice=self.bcdDevice,
                                   iManufacturer=0,
                                   iProduct=0,
                                   iSerialNumber=0,
                                   bNumConfigurations=self.bNumConfigurations).pack()
            self.send_usb_req(usb_req, ret, len(ret))
        elif control_req.wValue == 0x0200:  # Configuration descriptor
            handled = True
            ret = self.all_configurations[:control_req.wLength]
            self.send_usb_req(usb_req, ret, len(ret))
        elif control_req.wValue == 0x0300:  # String descriptor
            handled = True
            # Send empty string descriptor
            ret = b'\x04\x03\x09\x04'  # English (US) language descriptor
            self.send_usb_req(usb_req, ret, len(ret))
        else:
            print(f"Unknown descriptor type: {control_req.wValue:04x}")

        return handled

    def handle_set_configuration(self, control_req, usb_req):
        handled = False
        print("handle_set_configuration {}".format(control_req.wValue))
        handled = True
        self.send_usb_req(usb_req, b'', 0, 0)
        return handled

    def handle_usb_control(self, usb_req):
        control_req = StandardDeviceRequest()
        control_req.unpack(int_to_hex_string(usb_req.setup))
        handled = False
        print("  UC Request Type {}".format(control_req.bmRequestType))
        print("  UC Request {}".format(control_req.bRequest))
        print("  UC Value  {}".format(control_req.wValue))
        print("  UCIndex  {}".format(control_req.wIndex))
        print("  UC Length {}".format(control_req.wLength))
        
        if control_req.bmRequestType == 0x80:  # Host Request
            if control_req.bRequest == 0x06:  # Get Descriptor
                handled = self.handle_get_descriptor(control_req, usb_req)
            elif control_req.bRequest == 0x00:  # Get STATUS
                self.send_usb_req(usb_req, b"\x01\x00", 2)
                handled = True

        elif control_req.bmRequestType == 0x00:  # Host Request
            if control_req.bRequest == 0x09:  # Set Configuration
                handled = self.handle_set_configuration(control_req, usb_req)

        if not handled:
            print(f"Unhandled control request: {control_req.bmRequestType:02x} {control_req.bRequest:02x}")
            self.send_usb_req(usb_req, b'', 0, 0)  # Send empty response

    def handle_usb_request(self, usb_req):
        if usb_req.ep == 0:
            self.handle_usb_control(usb_req)
        else:
            self.handle_data(usb_req)

    def handle_data(self, usb_req):
        """Override this method in subclasses"""
        print(f"[USB] Default data handler for endpoint {usb_req.ep}")
        self.send_usb_req(usb_req, b'', 0, 0)


class USBContainer:
    def __init__(self):
        self.usb_devices = []

    def add_usb_device(self, usb_device):
        self.usb_devices.append(usb_device)

    def handle_attach(self):
        device = self.usb_devices[0]
        return OPREPImport(base=USBIPHeader(command=3, status=0),
                           usbPath=b'/sys/devices/pci0000:00/0000:00:01.2/usb1/1-1'.ljust(256, b'\x00'),
                           busID=b'1-1'.ljust(32, b'\x00'),
                           busnum=1,
                           devnum=2,
                           speed=2,  # High speed
                           idVendor=device.vendorID,
                           idProduct=device.productID,
                           bcdDevice=device.bcdDevice,
                           bDeviceClass=device.bDeviceClass,
                           bDeviceSubClass=device.bDeviceSubClass,
                           bDeviceProtocol=device.bDeviceProtocol,
                           bNumConfigurations=device.bNumConfigurations,
                           bConfigurationValue=device.bConfigurationValue,
                           bNumInterfaces=device.bNumInterfaces)

    def handle_device_list(self):
        usb_dev = self.usb_devices[0]
        
        # Create interface list for all interfaces
        interface_list = []
        for interface in usb_dev.configurations[0].interfaces:
            interface_list.append(USBInterface(
                bInterfaceClass=interface.bInterfaceClass,
                bInterfaceSubClass=interface.bInterfaceSubClass,
                bInterfaceProtocol=interface.bInterfaceProtocol
            ))
        
        response = OPREPDevList(base=USBIPHeader(command=5, status=0),
                               nExportedDevice=1,
                               usbPath=b'/sys/devices/pci0000:00/0000:00:01.2/usb1/1-1'.ljust(256, b'\x00'),
                               busID=b'1-1'.ljust(32, b'\x00'),
                               busnum=1,
                               devnum=2,
                               speed=2,
                               idVendor=usb_dev.vendorID,
                               idProduct=usb_dev.productID,
                               bcdDevice=usb_dev.bcdDevice,
                               bDeviceClass=usb_dev.bDeviceClass,
                               bDeviceSubClass=usb_dev.bDeviceSubClass,
                               bDeviceProtocol=usb_dev.bDeviceProtocol,
                               bNumConfigurations=usb_dev.bNumConfigurations,
                               bConfigurationValue=usb_dev.bConfigurationValue,
                               bNumInterfaces=usb_dev.bNumInterfaces)
        
        # Add the interface list to the response
        response.interfaces = interface_list
        
        return response

    def safe_recv(self, conn, size, timeout=5.0):
        """Safely receive data with timeout and proper error handling"""
        conn.settimeout(timeout)
        data = b''
        try:
            while len(data) < size:
                chunk = conn.recv(size - len(data))
                if not chunk:
                    print(f"[Server] Connection closed while receiving data (got {len(data)}/{size} bytes)")
                    return None
                data += chunk
                print(f"[Server] Received {len(chunk)} bytes ({len(data)}/{size} total)")
        except socket.timeout:
            print(f"[Server] Timeout while receiving data (got {len(data)}/{size} bytes)")
            return None
        except Exception as e:
            print(f"[Server] Error receiving data: {e}")
            return None
        finally:
            conn.settimeout(None)
        return data

    def run(self, ip='0.0.0.0', port=3240):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen(5)
        print(f"[Server] Listening on {ip}:{port}")
        
        while True:
            conn, addr = s.accept()
            print(f'[Server] Connection from: {addr}')
            
            attached = False
            req = USBIPHeader()
            
            try:
                while True:
                    if not attached:
                        # Handle initial protocol messages
                        print("[Server] Waiting for initial protocol message...")
                        data = self.safe_recv(conn, 8, timeout=10.0)
                        if data is None:
                            print("[Server] Failed to receive initial header")
                            break
                            
                        req.unpack(data)
                        print(f'[Server] Header command: {hex(req.command)}, version: {hex(req.version)}, status: {hex(req.status)}')
                        
                        if req.command == 0x8005:  # OP_REQ_DEVLIST
                            print('[Server] Sending device list')
                            response = self.handle_device_list()
                            conn.sendall(response.pack())
                            print(f'[Server] Sent device list response ({len(response.pack())} bytes)')
                            
                        elif req.command == 0x8003:  # OP_REQ_IMPORT
                            print('[Server] Handling device attach')
                            busid_data = self.safe_recv(conn, 32, timeout=5.0)
                            if busid_data is None:
                                print("[Server] Failed to receive bus ID")
                                break
                            
                            busid = busid_data.rstrip(b'\x00')
                            print(f'[Server] Bus ID: {busid}')
                            
                            response = self.handle_attach()
                            conn.sendall(response.pack())
                            print(f'[Server] Sent attach response ({len(response.pack())} bytes)')
                            print('[Server] Device attached, switching to USB mode')
                            attached = True
                            
                        else:
                            print(f'[Server] Unknown command: {hex(req.command)}')
                            break
                            
                    else:
                        # Handle USB requests
                        print('[Server] ================')
                        print('[Server] Waiting for USB request...')
                        
                        # Read the command header
                        cmd = USBIPCMDSubmit()
                        expected_size = cmd.size()
                        print(f"[Server] Expecting {expected_size} bytes for USB command")
                        
                        data = self.safe_recv(conn, expected_size, timeout=30.0)
                        if data is None:
                            print("[Server] Failed to receive USB command header")
                            break
                        
                        try:
                            cmd.unpack(data)
                            print(f"[Server] USB command: {hex(cmd.command)}")
                            print(f"[Server] seqnum: {hex(cmd.seqnum)}")
                            print(f"[Server] devid: {hex(cmd.devid)}")
                            print(f"[Server] direction: {hex(cmd.direction)}")
                            print(f"[Server] ep: {hex(cmd.ep)}")
                            print(f"[Server] flags: {hex(cmd.transfer_flags)}")
                            print(f"[Server] buffer_length: {cmd.transfer_buffer_length}")
                            
                            # Handle additional data if any
                            additional_data = b''
                            if cmd.transfer_buffer_length > 0:
                                print(f"[Server] Expecting {cmd.transfer_buffer_length} bytes of additional data")
                                additional_data = self.safe_recv(conn, cmd.transfer_buffer_length, timeout=10.0)
                                if additional_data is None:
                                    print("[Server] Failed to receive additional data")
                                    break
                                print(f"[Server] Additional data: {len(additional_data)} bytes")
                                if len(additional_data) > 0:
                                    print(f"[Server] Data preview: {additional_data[:min(64, len(additional_data))]}")
                            
                            # Create USB request
                            usb_req = USBRequest(seqnum=cmd.seqnum,
                                                 devid=cmd.devid,
                                                 direction=cmd.direction,
                                                 ep=cmd.ep,
                                                 flags=cmd.transfer_flags,
                                                 numberOfPackets=cmd.number_of_packets,
                                                 interval=cmd.interval,
                                                 setup=cmd.setup,
                                                 data=additional_data)
                            
                            # Handle the request
                            self.usb_devices[0].connection = conn
                            self.usb_devices[0].handle_usb_request(usb_req)
                            
                        except Exception as e:
                            print(f"[Server] Error processing USB command: {e}")
                            import traceback
                            traceback.print_exc()
                            break
                        
            except Exception as e:
                print(f"[Server] Error handling connection: {e}")
                import traceback
                traceback.print_exc()
            finally:
                print(f"[Server] Closing connection: {addr}")
                conn.close()