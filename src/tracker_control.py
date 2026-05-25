"""
MIT License

Copyright DragonDreams GmbH 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""Windows-only facial/lip tracker extension-unit control."""

from timeit import default_timer as timer
import ctypes
import ctypes.wintypes as ctwt
import logging
import time
import traceback

import comtypes as comt
import cv2 as cv
import numpy as np
import pygrabber.dshow_graph as pgdsg


c_void_p = ctypes.c_void_p
c_wchar_p = ctypes.c_wchar_p
c_ulong = ctypes.c_ulong
c_uint8 = ctypes.c_uint8
Structure = ctypes.Structure
POINTER = ctypes.POINTER
DWORD = ctwt.DWORD
COMMETHOD = comt.COMMETHOD
GUID = comt.GUID
REFIID = POINTER(GUID)
IUnknown = comt.IUnknown
HRESULT = ctypes.HRESULT

KSNODETYPE_DEV_SPECIFIC = GUID("{941C7AC0-C559-11D0-8A2B-00A0C9255AC1}")
GUID_EXT_CTRL_UNIT = GUID("{2ccb0bda-6331-4fdb-850e-79054dbd5671}")


class KSPROPERTY(Structure):
    _fields_ = [("Set", GUID), ("Id", c_ulong), ("Flags", c_ulong)]


class KSP_NODE(Structure):
    _fields_ = [
        ("Property", KSPROPERTY),
        ("NodeId", c_ulong),
        ("Reserved", c_ulong),
    ]


class KSTOPOLOGY_CONNECTION(Structure):
    _fields_ = [
        ("FromNode", c_ulong),
        ("FromNodePin", c_ulong),
        ("ToNode", c_ulong),
        ("ToNodePin", c_ulong),
    ]


class KSMETHOD(Structure):
    _fields_ = [("Set", GUID), ("Id", c_ulong), ("Flags", c_ulong)]


class KSEVENT(Structure):
    _fields_ = [("Set", GUID), ("Id", c_ulong), ("Flags", c_ulong)]


class IKsTopologyInfo(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{720D4AC0-7533-11D0-A5D6-28DB04C10000}")
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, "get_NumCategories", (["out"], POINTER(DWORD), "pdwNumCategories")),
        COMMETHOD([], HRESULT, "get_Category", (["in"], DWORD, "dwIndex"), (["out"], POINTER(GUID), "pCategory")),
        COMMETHOD([], HRESULT, "get_NumConnections", (["out"], POINTER(DWORD), "pdwNumConnections")),
        COMMETHOD([], HRESULT, "get_ConnectionInfo", (["in"], DWORD, "dwIndex"), (["out"], POINTER(KSTOPOLOGY_CONNECTION), "pConnectionInfo")),
        COMMETHOD([], HRESULT, "get_NodeName", (["in"], DWORD, "dwNodeId"), (["in"], c_wchar_p, "pwchNodeName"), (["in"], DWORD, "dwBufSize"), (["out"], POINTER(DWORD), "pdwNameLen")),
        COMMETHOD([], HRESULT, "get_NumNodes", (["out"], POINTER(DWORD), "pdwNumNodes")),
        COMMETHOD([], HRESULT, "get_NodeType", (["in"], DWORD, "dwNodeId"), (["out"], POINTER(GUID), "pNodeType")),
        COMMETHOD([], HRESULT, "CreateNodeInstance", (["in"], DWORD, "dwNodeId"), (["in"], REFIID, "iid"), (["out"], POINTER(POINTER(IUnknown)), "ppvObject")),
    ]


class IKsControl(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{28F54685-06FD-11D2-B27A-00A0C9223196}")
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, "KsProperty", (["in"], POINTER(KSP_NODE), "Property"), (["in"], c_ulong, "PropertyLength"), (["in"], c_void_p, "PropertyData"), (["in"], c_ulong, "DataLength"), (["in"], POINTER(c_ulong), "BytesReturned")),
        COMMETHOD([], HRESULT, "KsMethod", (["in"], POINTER(KSMETHOD), "Method"), (["in"], c_ulong, "MethodLength"), (["in", "out"], c_void_p, "MethodData"), (["in"], c_ulong, "DataLength"), (["out"], POINTER(c_ulong), "BytesReturned")),
        COMMETHOD([], HRESULT, "KsEvent", (["in"], POINTER(KSEVENT), "Event"), (["in"], c_ulong, "EventLength"), (["in", "out"], c_void_p, "EventData"), (["in"], c_ulong, "DataLength"), (["out"], POINTER(c_ulong), "BytesReturned")),
    ]


KSPROPERTY_TYPE_GET = 0x1
KSPROPERTY_TYPE_SET = 0x2
KSPROPERTY_TYPE_TOPOLOGY = 0x10000000


def _find_extension_node(topo: IKsTopologyInfo, guid: GUID) -> int | None:
    return next(
        (index for index in range(topo.get_NumNodes()) if topo.get_NodeType(index) == guid),
        None,
    )


def _control_property_request_len(control: IKsControl, selector: int, node: int) -> int:
    request = KSP_NODE(
        KSPROPERTY(
            GUID_EXT_CTRL_UNIT,
            selector,
            KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_TOPOLOGY,
        ),
        node,
        0,
    )
    bytes_returned = ctypes.c_ulong(0)
    try:
        control.KsProperty(
            request,
            ctypes.sizeof(request),
            None,
            0,
            bytes_returned,
        )
    except comt.COMError as error:
        if error.hresult == -2147024662:
            return int(bytes_returned.value)
    return 0


class TrackerController:
    """Activate and deactivate compatible camera data streams through DirectShow XU."""

    _XU_TASK_SET = 0x50
    _XU_TASK_GET = 0x51
    _XU_REG_SENSOR = 0xAB
    _XU_REG_SYSTEM = 0xA2
    _logger = logging.getLogger("lipcamera.TrackerController")

    def __init__(self, device: pgdsg.VideoInput, index: int) -> None:
        self._device = device
        self._device_index = index
        self._device_name = device.Name
        self._is_lip_camera = "HTC Lip Camera" in self._device_name
        self._xu_control: IKsControl | None = None
        self._xu_node_index: int | None = None

        TrackerController._logger.info("create tracker controller for '%s'", self._device_name)
        try:
            self._open_controller()
            self._init_common()
        except Exception:
            TrackerController._logger.error(
                "Camera extension-unit initialization failed:\n%s",
                traceback.format_exc(),
            )
            self._close_controller()
            raise

    @staticmethod
    def is_supported_camera(device: pgdsg.VideoInput) -> bool:
        check = any(
            camera_name in device.Name
            for camera_name in ("HTC Multimedia Camera", "HTC Lip Camera")
        )
        TrackerController._logger.info("is_supported_camera: '%s' -> %s", device.Name, check)
        return check

    def _init_common(self) -> None:
        self._data_buf_len = 384
        self._resize_data_buf()
        self._buffer_register = (ctypes.c_uint8 * 17)()
        self._debug = False
        self._detect_compatible_camera()
        self._activate_stream()

    def _resize_data_buf(self) -> None:
        self._buffer_send = (ctypes.c_uint8 * self._data_buf_len)()
        self._buffer_receive = (ctypes.c_uint8 * self._data_buf_len)()
        self._data_test = (ctypes.c_uint8 * self._data_buf_len)()
        self._data_test[0] = 0x51
        self._data_test[1] = 0x52
        if self._data_buf_len >= 256:
            self._data_test[254] = 0x53
            self._data_test[255] = 0x54

    def dispose(self) -> None:
        TrackerController._logger.info("dispose tracker controller")
        try:
            if self._xu_control:
                self._deactivate_stream()
        except Exception:
            TrackerController._logger.error(
                "Failed to disable camera stream during dispose:\n%s",
                traceback.format_exc(),
            )
        finally:
            self._close_controller()

    def process_frame(self, data: np.ndarray) -> np.ndarray:
        """Convert captured data to a displayable monochrome tracker image."""
        luminance = cv.split(data)[0]
        if not self._is_lip_camera:
            luminance = luminance[:, 0:200]
            luminance = cv.resize(luminance, (400, 400))
        return cv.merge((luminance, luminance, luminance))

    def _open_controller(self) -> None:
        if self._xu_control:
            return

        system_enum = pgdsg.SystemDeviceEnum().system_device_enum
        filter_enum = system_enum.CreateClassEnumerator(
            comt.GUID(pgdsg.DeviceCategories.VideoInputDevice),
            dwFlags=0,
        )
        moniker, count = filter_enum.Next(1)
        current = 0
        while current != self._device_index and count > 0:
            moniker, count = filter_enum.Next(1)
            current += 1
        if count <= 0:
            raise RuntimeError("DirectShow camera moniker could not be resolved")

        topology = self._device.instance.QueryInterface(IKsTopologyInfo)
        node_count = topology.get_NumNodes()
        TrackerController._logger.info("DirectShow topology node count: %s", node_count)

        self._xu_node_index = _find_extension_node(topology, KSNODETYPE_DEV_SPECIFIC)
        if self._xu_node_index is None:
            raise RuntimeError("No KSNODETYPE_DEV_SPECIFIC extension unit node found")

        TrackerController._logger.info("selected extension-unit node: %s", self._xu_node_index)
        xu_node: IUnknown = topology.CreateNodeInstance(
            self._xu_node_index,
            IUnknown._iid_,
        )
        self._xu_control = xu_node.QueryInterface(IKsControl)

        for selector in range(1, 17):
            try:
                payload_length = _control_property_request_len(
                    self._xu_control, selector, self._xu_node_index
                )
                if payload_length:
                    TrackerController._logger.info(
                        "XU selector[%s] payload length=%s",
                        selector,
                        payload_length,
                    )
            except Exception as error:
                TrackerController._logger.info(
                    "XU selector[%s] probe failed: %s",
                    selector,
                    error,
                )

    def _close_controller(self) -> None:
        self._xu_control = None

    def _xu_get_len(self, selector: int) -> int:
        return _control_property_request_len(
            self._xu_control,
            selector,
            self._xu_node_index,
        )

    def _xu_get_cur(self, selector: int, data: list[ctypes.c_uint8]) -> None:
        request = KSP_NODE(
            KSPROPERTY(
                GUID_EXT_CTRL_UNIT,
                selector,
                KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_TOPOLOGY,
            ),
            self._xu_node_index,
            0,
        )
        received = ctypes.c_ulong(0)
        self._xu_control.KsProperty(
            request,
            ctypes.sizeof(request),
            data,
            len(data),
            received,
        )

    def _xu_set_cur(self, selector: int, data: list[ctypes.c_uint8]) -> None:
        request = KSP_NODE(
            KSPROPERTY(
                GUID_EXT_CTRL_UNIT,
                selector,
                KSPROPERTY_TYPE_SET | KSPROPERTY_TYPE_TOPOLOGY,
            ),
            self._xu_node_index,
            0,
        )
        received = ctypes.c_ulong(0)
        self._xu_control.KsProperty(
            request,
            ctypes.sizeof(request),
            data,
            len(data),
            received,
        )

    def _set_cur(self, command: list[ctypes.c_uint8], timeout: float = 0.5) -> None:
        length = len(command)
        self._buffer_send[:length] = command
        self._xu_set_cur(2, self._buffer_send)

        buffer_length = len(self._buffer_receive)
        start_time = timer()
        while True:
            self._buffer_receive[:] = (ctypes.c_uint8 * buffer_length)(0)
            self._xu_get_cur(2, self._buffer_receive)
            if self._buffer_receive[0] == 0x56:
                if self._buffer_receive[1:17] == self._buffer_send[0:16]:
                    return
                raise RuntimeError("Extension-unit response did not match command")
            if self._buffer_receive[0] != 0x55:
                raise RuntimeError("Invalid extension-unit command response")

            if timer() - start_time > timeout:
                raise TimeoutError("Extension-unit command timed out")

    def _set_cur_no_resp(self, command: list[ctypes.c_uint8]) -> None:
        self._buffer_send[:] = (ctypes.c_uint8 * len(self._buffer_send))(0)
        self._buffer_send[:len(command)] = command
        self._xu_set_cur(2, self._buffer_send)

    def _init_register(
        self,
        command: int,
        register: int,
        address: int,
        address_length: int,
        value: int,
        value_length: int,
    ) -> None:
        buffer = self._buffer_register
        buffer[0] = command
        buffer[1] = register
        buffer[2] = 0x60
        buffer[3] = address_length
        buffer[4] = value_length
        buffer[5] = (address >> 24) & 0xFF
        buffer[6] = (address >> 16) & 0xFF
        buffer[7] = (address >> 8) & 0xFF
        buffer[8] = address & 0xFF
        buffer[9] = 0x90
        buffer[10] = 0x01
        buffer[11] = 0x00
        buffer[12] = 0x01
        buffer[13] = (value >> 24) & 0xFF
        buffer[14] = (value >> 16) & 0xFF
        buffer[15] = (value >> 8) & 0xFF
        buffer[16] = value & 0xFF

    def _set_register(
        self,
        register: int,
        address: int,
        value: int,
        timeout: float = 0.5,
    ) -> None:
        self._init_register(self._XU_TASK_SET, register, address, 1, value, 1)
        if timeout > 0:
            self._set_cur(self._buffer_register, timeout)
        else:
            self._set_cur_no_resp(self._buffer_register)

    def _set_register_sensor(self, address: int, value: int, timeout: float = 0.5) -> None:
        self._set_register(self._XU_REG_SENSOR, address, value, timeout)

    def _set_register_system(self, address: int, value: int) -> None:
        buffer = (ctypes.c_uint8 * self._data_buf_len)()
        buffer[0] = self._XU_TASK_SET
        buffer[1] = self._XU_REG_SYSTEM
        buffer[2] = 0x00
        buffer[3] = 0x04
        buffer[4] = 0x01
        buffer[5] = 0x80
        buffer[6] = 0x18
        buffer[7] = (address >> 8) & 0xFF
        buffer[8] = address & 0xFF
        buffer[10] = 0x01
        buffer[16] = value & 0xFF
        self._set_cur_no_resp(buffer)

    def _set_ir_led(self, enable: bool) -> None:
        value = 0x11 if enable else 0x03
        TrackerController._logger.info(
            "-> IR LED %s: system register 0x2246 = 0x%02x",
            "ON" if enable else "OFF",
            value,
        )
        self._set_register_system(0x2246, value)

    def _set_enable_stream(self, enable: bool) -> None:
        buffer = (ctypes.c_uint8 * 4)(
            self._XU_TASK_SET,
            0x14,
            0x00,
            0x01 if enable else 0x00,
        )
        self._set_cur_no_resp(buffer)

    def _detect_compatible_camera(self) -> None:
        length = self._xu_get_len(2)
        TrackerController._logger.info("extension-unit selector 2 payload length: %s", length)
        if length <= 0 or length > 4096:
            raise RuntimeError(
                "Invalid extension-unit selector 2 payload length: {}".format(length)
            )
        if length != self._data_buf_len:
            self._data_buf_len = length
            self._resize_data_buf()
        if length not in (64, 384):
            TrackerController._logger.warning(
                "Unrecognized payload length %s; continuing experimentally",
                length,
            )

    def _activate_stream(self) -> None:
        TrackerController._logger.info("activate camera stream")
        if self._is_lip_camera:
            self._set_enable_stream(False)
            time.sleep(0.25)
            self._set_enable_stream(True)
            time.sleep(0.25)
            self._set_ir_led(True)
            time.sleep(0.25)
            return

        self._set_cur(self._data_test)
        self._set_enable_stream(False)
        time.sleep(0.25)

        self._set_cur(self._data_test)
        self._set_register_sensor(0x00, 0x40)
        self._set_register_sensor(0x08, 0x01)
        self._set_register_sensor(0x70, 0x00)
        self._set_register_sensor(0x02, 0xFF)
        self._set_register_sensor(0x03, 0xFF)
        self._set_register_sensor(0x04, 0xFF)
        self._set_register_sensor(0x0E, 0x00)
        self._set_register_sensor(0x05, 0xB2)
        self._set_register_sensor(0x06, 0xB2)
        self._set_register_sensor(0x07, 0xB2)
        self._set_register_sensor(0x0F, 0x03)

        self._set_cur(self._data_test)
        self._set_enable_stream(True)
        time.sleep(0.25)

    def _deactivate_stream(self) -> None:
        TrackerController._logger.info("deactivate camera stream")
        if self._is_lip_camera:
            self._set_ir_led(False)
            time.sleep(0.25)
            self._set_enable_stream(False)
            time.sleep(0.25)
            return

        self._set_cur(self._data_test)
        self._set_enable_stream(False)
        time.sleep(0.25)