from datetime import datetime
# import logging
import uuid

import firebase_admin
from firebase_admin import firestore

from sds011_v2 import SDS011


# logging.basicConfig(level=logging.DEBUG)

# Credentials pulled from file named in GOOGLE_APPLICATION_CREDENTIALS os env var
app = firebase_admin.initialize_app()
db = firestore.client()

# TODO: Automatically find the device based on "usbserial-*"
sensor = SDS011('/dev/tty.usbserial-1460', use_query_mode=False, work_period=1)
device_mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])

for _ in range(4):
    pm25, pm10 = sensor.read()  # This will block for work_period minutes
    print(f'At {datetime.now()}  PM2.5: {pm25} μg/m³, PM10: {pm10} μg/m³')
    reading_id = str(uuid.uuid1())
    data = {
        u'device': device_mac,
        u'pm2.5': pm25,
        u'pm10': pm10,
        u'time': datetime.utcnow()
    }
    db.collection(u'readings').document(reading_id).set(data)
