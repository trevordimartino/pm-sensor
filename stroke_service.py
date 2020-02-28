from datetime import datetime

from flask import Flask
from flask import jsonify

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


@app.route('/stroke', methods=["GET"])
def get_pen_stroke():
    aq_reading = get_air_quality_reading()
    pen_stroke = gen_pen_stroke(aq_reading)
    return jsonify(pen_stroke)


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

    # response.headers.add('Access-Control-Allow-Origin', r)
    # response.headers.add('Access-Control-Allow-Credentials', 'true')
    # response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    # response.headers.add('Access-Control-Allow-Headers', 'Cache-Control')
    # response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With')
    # response.headers.add('Access-Control-Allow-Headers', 'Authorization')
    # response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
