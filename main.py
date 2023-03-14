from PCF8583 import PCF8583
from PCF8583.constants import MODE_EVENT_COUNTER
from time import sleep

counter = PCF8583()
counter.reset()
counter.set_mode(MODE_EVENT_COUNTER)

while True:
    print(counter.get_count())
    sleep(1)
