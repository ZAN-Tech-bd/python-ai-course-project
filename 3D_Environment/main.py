"""Open City - a small GTA-style open-world game built with Ursina/Python.

Walk or drive around a procedurally generated city, complete delivery
missions for cash, and enjoy a full day/night cycle with traffic and
pedestrians going about their business.

Run with:  python main.py
"""

import random
from ursina import (
    Ursina, Entity, Sky, DirectionalLight, AmbientLight, color, time,
    mouse, application, window, held_keys, Vec3,
)

import settings as S
from world import City
from entities import Player, Car, Pedestrian, TrafficCar, ThirdPersonCamera
from missions import MissionManager
from hud import HUD, MainMenu, PauseMenu

app = Ursina()

window.title = 'Open City'
window.borderless = False
window.fullscreen = True
window.exit_button.visible = False
window.fps_counter.enabled = False

# ------------------------------------------------------------- world setup
sky = Sky(texture='sky_default')
sun = DirectionalLight(shadows=True)
sun.rotation = (45, 45, 0)
ambient = AmbientLight(color=color.rgb32(140, 140, 160))

city = City()
camera_rig = ThirdPersonCamera()

spawn = Vec3(0, 0, 0)
player = Player(city, camera_rig, position=(spawn.x, 0, spawn.z))
camera_rig.set_target(player, S.CAM_DISTANCE_WALK, S.CAM_HEIGHT_WALK)

drivable_cars = []
car_colors = [color.rgb32(200, 40, 40), color.rgb32(40, 90, 200), color.rgb32(230, 200, 40)]
for i, c in enumerate(car_colors):
    ang = i * (360 / len(car_colors))
    pos = Vec3(spawn.x + 6 * random.uniform(0.8, 1.2), 0.4, spawn.z + 4 + i * 4)
    drivable_cars.append(Car(city, position=pos, body_color=c))

pedestrians = [Pedestrian(random.choice(city.pedestrian_loops)) for _ in range(14)]
traffic_cars = [TrafficCar(random.choice(city.traffic_loops)) for _ in range(8)]

mission = MissionManager(city, player, get_car=lambda: player.in_car)
hud = HUD(mission, player)
hud_ready = False  # HUD starts hidden until Play is pressed

# ---------------------------------------------------------------- game state
state = {'mode': 'menu'}  # 'menu' | 'playing' | 'paused'


def start_game():
    state['mode'] = 'playing'
    application.paused = False
    camera_rig.active = True
    mouse.locked = True
    mouse.visible = False


def resume_game():
    state['mode'] = 'playing'
    application.paused = False
    mouse.locked = True
    mouse.visible = False
    pause_menu.set_visible(False)


def pause_game():
    state['mode'] = 'paused'
    application.paused = True
    mouse.locked = False
    mouse.visible = True
    pause_menu.set_visible(True)


def quit_game():
    application.quit()


main_menu = MainMenu(on_play=start_game)
pause_menu = PauseMenu(on_resume=resume_game, on_quit=quit_game)

# freeze all gameplay entities until the player presses Play
application.paused = True
camera_rig.active = False
mouse.locked = False


def try_toggle_vehicle():
    if player.in_car:
        car = player.in_car
        player.exit_car(car)
        camera_rig.set_target(player, S.CAM_DISTANCE_WALK, S.CAM_HEIGHT_WALK)
        return
    nearest, nearest_dist = None, S.ENTER_EXIT_RANGE
    for c in drivable_cars:
        d = (c.position - player.position).length()
        if d < nearest_dist:
            nearest, nearest_dist = c, d
    if nearest:
        player.enter_car(nearest)
        camera_rig.set_target(nearest, S.CAM_DISTANCE_CAR, S.CAM_HEIGHT_CAR)


# --------------------------------------------------------------- day/night
_day_timer = random.uniform(S.DAY_LENGTH_SECONDS * 0.28, S.DAY_LENGTH_SECONDS * 0.32)
_lights_on = False

DAY = color.rgb32(130, 180, 255)
SUNSET = color.rgb32(255, 140, 90)
NIGHT = color.rgb32(12, 12, 40)


def _lerp_color(a, b, t):
    return color.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t,
                       a.b + (b.b - a.b) * t, 1)


def update_day_night(dt):
    global _day_timer, _lights_on
    _day_timer = (_day_timer + dt) % S.DAY_LENGTH_SECONDS
    t = _day_timer / S.DAY_LENGTH_SECONDS

    if t < 0.25:
        sky_col = _lerp_color(NIGHT, DAY, t / 0.25)
        brightness = t / 0.25
    elif t < 0.5:
        sky_col = DAY
        brightness = 1
    elif t < 0.6:
        sky_col = _lerp_color(DAY, SUNSET, (t - 0.5) / 0.1)
        brightness = 1
    elif t < 0.75:
        sky_col = _lerp_color(SUNSET, NIGHT, (t - 0.6) / 0.15)
        brightness = 1 - (t - 0.6) / 0.15
    else:
        sky_col = NIGHT
        brightness = 0.08

    sky.color = sky_col
    sun.rotation_x = 20 + t * 320
    sun.color = _lerp_color(color.rgb32(30, 30, 40), color.rgb32(255, 250, 235), brightness)
    ambient.color = color.rgb32(int(60 + 100 * brightness), int(60 + 100 * brightness),
                                 int(80 + 90 * brightness))

    should_light = brightness < 0.4
    if should_light != _lights_on:
        _lights_on = should_light
        for lamp in city.streetlights:
            lamp.color = color.rgb32(255, 235, 150) if should_light else color.rgb32(120, 110, 90)


# -------------------------------------------------------------- main loop
def update():
    update_day_night(time.dt)

    if state['mode'] != 'playing':
        return

    mission.update()
    driving_car = player.in_car
    hud.update(S.CITY_SPAN, driving_car)

    if player.health <= 0:
        # "wasted" - respawn at origin, small cash penalty
        if player.in_car:
            player.exit_car(player.in_car)
            camera_rig.set_target(player, S.CAM_DISTANCE_WALK, S.CAM_HEIGHT_WALK)
        player.position = Vec3(0, 0, 0)
        player.health = S.PLAYER_MAX_HEALTH
        mission.money = max(0, mission.money - 50)
        mission.flash_message = "Wasted! Lost $50 and respawned."
        mission.flash_timer = 3


def input(key):
    if key == 'f11':
        window.fullscreen = not window.fullscreen
        return

    if key == 'escape':
        if state['mode'] == 'playing':
            pause_game()
        elif state['mode'] == 'paused':
            resume_game()
        return

    if state['mode'] != 'playing':
        return

    if key == 'e':
        try_toggle_vehicle()
    elif key == 'h':
        hud.toggle_help()
    elif key == 'm':
        hud.map_size = 0.42 if hud.map_size < 0.35 else 0.28


app.run()
