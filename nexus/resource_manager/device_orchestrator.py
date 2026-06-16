"""
NexusCore — منسّق الأجهزة الذكية
بديل آمن لـ drone_controller.py — يدير وينسق الأجهزة المتصلة (IoT).
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("nexus.resource.device")


class DeviceStatus(Enum):
    ONLINE   = "online"
    OFFLINE  = "offline"
    IDLE     = "idle"
    BUSY     = "busy"
    ERROR    = "error"


@dataclass
class Device:
    device_id: str
    name: str
    device_type: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    last_seen: float = field(default_factory=time.time)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    _handler: Optional[Callable] = field(default=None, repr=False)


@dataclass
class TaskResult:
    task_id: str
    device_id: str
    command: str
    success: bool
    output: Optional[str]
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class DeviceOrchestrator:
    """ينسق الأجهزة الذكية المتصلة ويوزع المهام"""

    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.task_history: List[TaskResult] = []
        logger.info("🤖 DeviceOrchestrator initialized")

    def register_device(self, device_id: str, name: str, device_type: str,
                        capabilities: Optional[List[str]] = None,
                        handler: Optional[Callable] = None) -> Device:
        device = Device(
            device_id=device_id, name=name, device_type=device_type,
            status=DeviceStatus.ONLINE,
            capabilities=capabilities or [],
            _handler=handler,
        )
        self.devices[device_id] = device
        logger.info(f"✅ Device registered: {name} ({device_type})")
        return device

    def deregister(self, device_id: str) -> bool:
        dev = self.devices.pop(device_id, None)
        if dev:
            logger.info(f"Device removed: {dev.name}")
        return dev is not None

    def send_command(self, device_id: str, command: str,
                     params: Optional[Dict] = None) -> TaskResult:
        device = self.devices.get(device_id)
        start = time.time()
        task_id = uuid.uuid4().hex[:8]

        if not device:
            return TaskResult(task_id=task_id, device_id=device_id,
                              command=command, success=False,
                              output="Device not found",
                              duration_ms=0.0)

        if device.status == DeviceStatus.OFFLINE:
            return TaskResult(task_id=task_id, device_id=device_id,
                              command=command, success=False,
                              output="Device is offline",
                              duration_ms=0.0)

        device.status = DeviceStatus.BUSY
        output: Optional[str] = None
        success = False

        try:
            if device._handler:
                result = device._handler(command, params or {})
                output = str(result)
                success = True
            else:
                output = f"Simulated: {command} on {device.name}"
                success = True
            device.status = DeviceStatus.IDLE
        except Exception as exc:
            output = str(exc)
            device.status = DeviceStatus.ERROR
            logger.error(f"Command failed on {device_id}: {exc}")

        device.last_seen = time.time()
        result_obj = TaskResult(
            task_id=task_id, device_id=device_id, command=command,
            success=success, output=output,
            duration_ms=round((time.time() - start) * 1000, 2),
        )
        self.task_history.append(result_obj)
        return result_obj

    def get_online_devices(self, device_type: Optional[str] = None) -> List[Device]:
        return [
            d for d in self.devices.values()
            if d.status in (DeviceStatus.ONLINE, DeviceStatus.IDLE)
            and (device_type is None or d.device_type == device_type)
        ]

    def get_stats(self) -> Dict:
        status_counts: Dict[str, int] = {}
        for d in self.devices.values():
            status_counts[d.status.value] = status_counts.get(d.status.value, 0) + 1
        return {
            "total_devices": len(self.devices),
            "by_status": status_counts,
            "total_tasks": len(self.task_history),
            "successful_tasks": sum(1 for t in self.task_history if t.success),
        }
