from datetime import datetime
import json

from flask import Flask

from generate_windy_pen_data import gen_pen_stroke
from sds011_v2 import SDS011


DEVICE_LOCATION = '/dev/tty.usbserial-1440'
sensor = SDS011(DEVICE_LOCATION)
print('Sensor initialized!')


def get_air_quality_reading():
    pm25, pm10 = sensor.query()
    print(f'At {datetime.now()}  PM2.5: {pm25} μg/m³, PM10: {pm10} μg/m³')
    return (pm25, pm10)


app = Flask(__name__)


@app.route('/stroke')
def get_pen_stroke():
    aq_reading = get_air_quality_reading()
    pen_stroke = gen_pen_stroke(aq_reading)
    return json.dumps(pen_stroke)
