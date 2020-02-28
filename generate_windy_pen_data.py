import json
from math import sin, cos, pi

import pyro


def gen_start_state():
    # TODO: Maybe loop the PM sensor into starting position?
    x = pyro.sample('start_x', pyro.distributions.Uniform(0.0, 1.0)).item()
    y = pyro.sample('start_y', pyro.distributions.Uniform(0.0, 1.0)).item()

    # TODO: Maybe loop the PM sensor into the speed?
    speed = pyro.sample('start_speed', pyro.distributions.Uniform(0.0, 1.0)).item()
    return (x, y), speed


def gen_next_segment(aq_reading, direction=None, last_direction_change=None):
    """
    Inputting a direction will influence the generation of the next segment
    """
    # Typical pm25 reading has mean ~0.5 and std ~0.1 during the day, but could get above 1
    #                      at night ~0.35        ~0.06
    # Typical pm10 reading has mean ~1.5 and std ~0.8 during the day, and can spike to 4
    #                      at night ~0.61        ~0.11

    (pm25, pm10) = aq_reading
    acceleration = pyro.sample('acceleration', pyro.distributions.Normal(1.0, 0.02 * pm25)).item()
    length = pyro.sample('length', pyro.distributions.Normal(60, 5)).item()

    if direction is None:
        # TODO: Maybe loop the PM sensor into the direction?
        direction = pyro.sample('direction', pyro.distributions.Uniform(0.0, 2.0 * pi)).item()
        direction_change = 0
    else:
        direction_change = pyro.sample('direction_change', pyro.distributions.Normal(0.0, pi / 12.0)).item()
        direction_change = direction_change * pm10
        direction = direction + direction_change

    return direction, direction_change, acceleration, length


def gen_pen_stroke(aq_reading):
    start_point, start_speed = gen_start_state()
    direction, direction_change, acceleration, length = gen_next_segment(aq_reading)
    pen_stroke = {
        "location": start_point,
        "speed": start_speed,
        "segments": [{
            "unit_direction": [cos(direction), sin(direction)],
            "acceleration": acceleration,
            "length": length
        }]
    }

    one_more = pyro.sample('one_more', pyro.distributions.Bernoulli(0.99)).item()
    while one_more:
        direction, direction_change, acceleration, length = gen_next_segment(aq_reading, direction, direction_change)
        pen_stroke["segments"].append({
            "unit_direction": [cos(direction), sin(direction)],
            "acceleration": acceleration,
            "length": length
        })
        one_more = pyro.sample('one_more', pyro.distributions.Bernoulli(0.9)).item()

    return pen_stroke


if __name__ == "__main__":
    pen_strokes = [gen_pen_stroke() for _ in range(100)]
    with open('fake_data.json', 'w') as f:
        json.dump(pen_strokes, f)
