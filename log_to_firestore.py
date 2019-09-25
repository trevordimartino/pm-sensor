from datetime import datetime
import logging
import socket
import uuid

import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials

from sds011_v2 import SDS011


DEVICE_LOCATION = '/dev/ttyUSB0'
WORK_PERIOD = 10  # Number of minutes between readings, up to 30
GOOGLE_APP_CREDS_PATH = '/home/pi/Downloads/pm-sensor-creds.json'

logging.basicConfig(level=logging.DEBUG)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))  # Google's DNS
    ip_address = s.getsockname()[0]

# Credentials pulled from file named in GOOGLE_APPLICATION_CREDENTIALS os env var
creds = credentials.Certificate(GOOGLE_APP_CREDS_PATH)
app = firebase_admin.initialize_app(creds)
db = firestore.client()

sensor = SDS011(DEVICE_LOCATION, use_query_mode=False, work_period=WORK_PERIOD)
device_mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])

for _ in range(4):
    pm25, pm10 = sensor.read()  # This will block for up to WORK_PERIOD minutes
    print(f'At {datetime.now()}  PM2.5: {pm25} μg/m³, PM10: {pm10} μg/m³')
    reading_id = str(uuid.uuid1())
    data = {
        u'device': device_mac,
        u'ip-address': ip_address,
        u'pm2.5': pm25,
        u'pm10': pm10,
        u'time': datetime.utcnow()
    }
    db.collection(u'readings').document(reading_id).set(data)
