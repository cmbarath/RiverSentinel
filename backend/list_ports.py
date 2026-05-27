
import serial.tools.list_ports
ports = list(serial.tools.list_ports.comports())
for i, p in enumerate(ports):
    print(f"[{i}] {p.device} - {p.description}")
