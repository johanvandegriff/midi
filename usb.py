#https://stackoverflow.com/questions/51007632/how-to-monitor-usb-devices-insertion#51011386
from pyudev import Context, Monitor
import time

context = Context()
monitor = Monitor.from_netlink(context)

#optional:
# monitor.filter_by(subsystem='usb')
monitor.filter_by(subsystem='usb', device_type='usb_device')
# monitor.filter_by(subsystem='usb', device_type='usb_interface')

while True:
    device = monitor.poll(timeout=10)
    if device:
        # print('{0.action}: {0} {1}'.format(device, device.properties))
        print(dict(device.properties))
    # time.sleep(0.2)
    print("tick")