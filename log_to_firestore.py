import logging
import uuid

import firebase_admin
from firebase_admin import firestore

from sds011_v2 import SDS011


logging.basicConfig(level=logging.DEBUG)

# Credentials pulled from file named in GOOGLE_APPLICATION_CREDENTIALS os env var
app = firebase_admin.initialize_app()
db = firestore.client()

# TODO: Automatically find the device based on "usbserial-*"
sensor = SDS011('/dev/tty.usbserial-1460', use_query_mode=False, work_period=1)

reading = sensor.read()
print(reading)
