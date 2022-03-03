#https://stackoverflow.com/questions/51007632/how-to-monitor-usb-devices-insertion#51011386
from pyudev import Context, Monitor, MonitorObserver
import time

context = Context()
monitor = Monitor.from_netlink(context)
monitor.filter_by(subsystem='usb')
def print_device_event(device):
    print('background event {0.action}: {0.device_path}'.format(device))
observer = MonitorObserver(monitor, callback=print_device_event, name='monitor-observer')
observer.daemon
observer.start()

while True:
    time.sleep(1)