"""Player, drivable Car, wandering Pedestrians, looping TrafficCars, and the
third-person camera rig that follows whichever one is currently active."""

import math
import random
from ursina import Entity, Vec3, color, time, held_keys, mouse, camera, raycast, destroy

import settings as S


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _resolve_building_collision(pos, radius, buildings):
    for b in buildings:
        dx = pos.x - b['x']
        dz = pos.z - b['z']
        half = b['half'] + radius
        if -half < dx < half and -half < dz < half:
            overlap_x = half - abs(dx)
            overlap_z = half - abs(dz)
            if overlap_x < overlap_z:
                pos.x += overlap_x if dx > 0 else -overlap_x
            else:
                pos.z += overlap_z if dz > 0 else -overlap_z
    return pos


def _clamp_to_city(pos, margin=14):
    limit = S.HALF_CITY + margin
    pos.x = _clamp(pos.x, -limit, limit)
    pos.z = _clamp(pos.z, -limit, limit)
    return pos


# ---------------------------------------------------------------- camera
class ThirdPersonCamera(Entity):
    """A rotating pivot the player mouse-orbits; camera pulls in on collision."""

    def __init__(self):
        super().__init__()
        self.target = None
        self.yaw = 0.0
        self.pitch = 12.0
        self.distance = S.CAM_DISTANCE_WALK
        self.height = S.CAM_HEIGHT_WALK
        self.active = True

    def set_target(self, target, distance, height):
        self.target = target
        self.distance = distance
        self.height = height

    def update(self):
        if not self.target or not self.active:
            return
        self.yaw += mouse.velocity[0] * S.MOUSE_SENSITIVITY
        self.pitch = _clamp(self.pitch - mouse.velocity[1] * S.MOUSE_SENSITIVITY, -25, 55)
        self.rotation = (self.pitch, self.yaw, 0)

        pivot_pos = self.target.world_position + Vec3(0, self.height, 0)
        self.position = pivot_pos

        desired_offset = self.forward * self.distance
        hit = raycast(pivot_pos, direction=-self.forward, distance=self.distance,
                       ignore=[self.target, self], debug=False)
        final_distance = hit.distance * 0.85 if hit.hit else self.distance
        final_distance = max(final_distance, 1.5)

        camera.position = pivot_pos - self.forward * final_distance
        camera.rotation = self.rotation

    def flat_forward(self):
        rad = math.radians(self.yaw)
        return Vec3(math.sin(rad), 0, math.cos(rad))

    def flat_right(self):
        f = self.flat_forward()
        return Vec3(f.z, 0, -f.x)


# ---------------------------------------------------------------- player
class Player(Entity):
    def __init__(self, city, camera_rig, position=(0, 0, 0)):
        super().__init__(position=position)
        self.city = city
        self.cam = camera_rig
        self.velocity_y = 0
        self.grounded = True
        self.health = S.PLAYER_MAX_HEALTH
        self.stamina = S.PLAYER_MAX_STAMINA
        self.in_car = None
        self.facing = 0

        # simple low-poly character look
        self.body = Entity(parent=self, model='cube', y=0.9, scale=(0.7, 1.0, 0.4),
                            color=color.rgb32(60, 90, 160))
        self.head = Entity(parent=self, model='sphere', y=1.65, scale=0.42,
                            color=color.rgb32(235, 200, 165))
        self.leg_l = Entity(parent=self, model='cube', position=(-0.18, 0.3, 0), scale=(0.28, 0.6, 0.32),
                             color=color.rgb32(35, 35, 45))
        self.leg_r = Entity(parent=self, model='cube', position=(0.18, 0.3, 0), scale=(0.28, 0.6, 0.32),
                             color=color.rgb32(35, 35, 45))

    def update(self):
        if self.in_car is not None:
            return  # movement handled by the car while driving

        move_x = held_keys['d'] - held_keys['a']
        move_z = held_keys['w'] - held_keys['s']
        moving = bool(move_x or move_z)

        sprint = held_keys['shift'] and self.stamina > 0 and moving
        speed = S.PLAYER_RUN_SPEED if sprint else S.PLAYER_WALK_SPEED

        if sprint:
            self.stamina = max(0, self.stamina - S.STAMINA_DRAIN * time.dt)
        else:
            self.stamina = min(S.PLAYER_MAX_STAMINA, self.stamina + S.STAMINA_REGEN * time.dt)

        if moving:
            fwd = self.cam.flat_forward()
            right = self.cam.flat_right()
            direction = (fwd * move_z + right * move_x)
            if direction.length() > 0:
                direction = direction.normalized()
                new_pos = self.position + direction * speed * time.dt
                new_pos = _resolve_building_collision(new_pos, S.PLAYER_RADIUS, self.city.buildings)
                new_pos = _clamp_to_city(new_pos)
                new_pos.y = self.y
                self.position = new_pos
                target_facing = math.degrees(math.atan2(direction.x, direction.z))
                diff = (target_facing - self.facing + 180) % 360 - 180
                self.facing += diff * min(1, time.dt * 10)
                self.rotation_y = self.facing

        # jump / gravity
        if self.grounded and held_keys['space']:
            self.velocity_y = math.sqrt(2 * 9.8 * S.PLAYER_JUMP_HEIGHT)
            self.grounded = False

        self.velocity_y -= 9.8 * 2 * time.dt
        self.y += self.velocity_y * time.dt
        if self.y <= 0:
            self.y = 0
            self.velocity_y = 0
            self.grounded = True

        # slow health regen when not in a car
        if self.health < S.PLAYER_MAX_HEALTH:
            self.health = min(S.PLAYER_MAX_HEALTH, self.health + 3 * time.dt)

    def enter_car(self, car):
        self.in_car = car
        self.enabled = False
        car.driver = self

    def exit_car(self, car):
        side = car.right if hasattr(car, 'right') else Vec3(1, 0, 0)
        self.position = car.position + side * 2.5 + Vec3(0, 0, 0)
        self.position = _clamp_to_city(self.position)
        self.enabled = True
        self.in_car = None
        car.driver = None


# ------------------------------------------------------------------ car
class Car(Entity):
    def __init__(self, city, position=(0, 0.4, 0), body_color=None):
        super().__init__(position=position)
        self.city = city
        self.driver = None
        self.speed = 0.0
        self.rotation_y = random.choice([0, 90, 180, 270])

        c = body_color or color.rgb32(200, 40, 40)
        self.chassis = Entity(parent=self, model='cube', scale=(1.7, 0.7, 3.6), y=0.5, color=c)
        self.cabin = Entity(parent=self, model='cube', scale=(1.4, 0.5, 1.8), y=1.05, z=-0.2,
                             color=color.rgba32(150, 200, 230, 180))
        wheel_positions = [(-0.85, 0.15, 1.2), (0.85, 0.15, 1.2), (-0.85, 0.15, -1.2), (0.85, 0.15, -1.2)]
        for wx, wy, wz in wheel_positions:
            Entity(parent=self, model='cube', position=(wx, wy, wz), scale=(0.35, 0.35, 0.5),
                   color=color.rgb32(20, 20, 20))
        self.headlight_l = Entity(parent=self, model='sphere', position=(-0.6, 0.5, 1.8), scale=0.18,
                                   color=color.rgb32(255, 255, 220))
        self.headlight_r = Entity(parent=self, model='sphere', position=(0.6, 0.5, 1.8), scale=0.18,
                                   color=color.rgb32(255, 255, 220))

    def update(self):
        if self.driver is None:
            # idle drag so unattended cars roll to a stop
            self.speed *= max(0, 1 - S.CAR_DRAG * time.dt)
            if abs(self.speed) < 0.05:
                self.speed = 0
                return
        else:
            throttle = held_keys['w'] - held_keys['s']
            steer = held_keys['d'] - held_keys['a']

            if throttle > 0:
                self.speed += S.CAR_ACCEL * time.dt
            elif throttle < 0:
                self.speed -= S.CAR_BRAKE * time.dt if self.speed > 0 else S.CAR_ACCEL * 0.6 * time.dt
            else:
                self.speed -= math.copysign(min(abs(self.speed), S.CAR_DRAG * time.dt), self.speed)

            self.speed = _clamp(self.speed, -S.CAR_REVERSE_SPEED, S.CAR_MAX_SPEED)

            speed_factor = _clamp(abs(self.speed) / 6, 0, 1)
            if abs(self.speed) > 0.05:
                turn_dir = 1 if self.speed >= 0 else -1
                self.rotation_y += steer * S.CAR_TURN_SPEED * speed_factor * turn_dir * time.dt

        new_pos = self.position + self.forward * self.speed * time.dt
        pre_collision = Vec3(new_pos)
        new_pos = _resolve_building_collision(new_pos, S.CAR_RADIUS, self.city.buildings)
        new_pos = _clamp_to_city(new_pos)
        if new_pos != pre_collision:
            # hit something solid: kill most of the speed (bump)
            if abs(self.speed) > 12 and self.driver:
                self.driver.health = max(0, self.driver.health - 8)
            self.speed *= -0.25
        new_pos.y = self.y
        self.position = new_pos


# ------------------------------------------------------------ pedestrian
class Pedestrian(Entity):
    def __init__(self, loop, speed=None):
        start = loop[0]
        super().__init__(position=(start.x, 0, start.z))
        self.loop = loop
        self.index = 0
        self.speed = speed or random.uniform(1.1, 2.0)
        self.t = random.uniform(0, 10)

        shirt = random.choice([color.rgb32(200, 60, 60), color.rgb32(60, 150, 90),
                                color.rgb32(60, 90, 200), color.rgb32(200, 180, 60)])
        self.body = Entity(parent=self, model='cube', y=0.8, scale=(0.5, 0.9, 0.3), color=shirt)
        self.head = Entity(parent=self, model='sphere', y=1.4, scale=0.35,
                            color=color.rgb32(230, 195, 160))

    def update(self):
        target = self.loop[self.index]
        direction = Vec3(target.x - self.x, 0, target.z - self.z)
        dist = direction.length()
        if dist < 0.6:
            self.index = (self.index + 1) % len(self.loop)
            return
        direction = direction.normalized()
        self.position += direction * self.speed * time.dt
        self.rotation_y = math.degrees(math.atan2(direction.x, direction.z))
        self.t += time.dt * 6
        self.y = abs(math.sin(self.t)) * 0.05


# ------------------------------------------------------------- traffic car
class TrafficCar(Entity):
    def __init__(self, loop, speed=None, body_color=None):
        start = loop[0]
        super().__init__(position=(start.x, 0.4, start.z))
        self.loop = loop
        self.index = 1
        self.speed = speed or random.uniform(4, 7)

        c = body_color or random.choice([color.rgb32(60, 60, 200), color.rgb32(210, 210, 210),
                                          color.rgb32(40, 40, 40), color.rgb32(200, 150, 30)])
        self.chassis = Entity(parent=self, model='cube', scale=(1.6, 0.65, 3.4), y=0.45, color=c)
        for wx, wz in [(-0.8, 1.1), (0.8, 1.1), (-0.8, -1.1), (0.8, -1.1)]:
            Entity(parent=self, model='cube', position=(wx, 0.14, wz), scale=(0.32, 0.32, 0.48),
                   color=color.rgb32(15, 15, 15))

    def update(self):
        target = self.loop[self.index]
        direction = Vec3(target.x - self.x, 0, target.z - self.z)
        dist = direction.length()
        if dist < 0.8:
            self.index = (self.index + 1) % len(self.loop)
            return
        direction = direction.normalized()
        self.position += direction * self.speed * time.dt
        self.rotation_y = math.degrees(math.atan2(direction.x, direction.z))
