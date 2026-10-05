"""Simple GTA-style 'go to the marker' delivery mission loop."""

import math
import random
from ursina import Entity, Vec3, color, time

import settings as S


class MissionManager:
    def __init__(self, city, player, get_car):
        """get_car: zero-arg callable returning the car the player is currently
        driving (or None), so proximity checks work on foot or by vehicle."""
        self.city = city
        self.player = player
        self.get_car = get_car
        self.money = 0
        self.delivered = 0
        self.flash_message = ""
        self.flash_timer = 0
        self.marker = None
        self._spawn_marker()

    def _spawn_marker(self):
        if self.marker:
            self.marker.disable()
            from ursina import destroy
            destroy(self.marker)

        point = self.city.random_road_point()
        # nudge away from player so it's never instantly complete
        while (point - self.player.position).length() < 12:
            point = self.city.random_road_point()

        self.marker = Entity(model='diamond', position=(point.x, 1.4, point.z),
                              scale=1, color=color.gold)
        self.target_point = point
        self._t = 0

    def update(self):
        if self.marker:
            self._t += time.dt
            self.marker.rotation_y += 90 * time.dt
            self.marker.y = 1.4 + math.sin(self._t * 2) * 0.25

            actor_pos = self.get_car().position if self.get_car() else self.player.position
            flat = Vec3(actor_pos.x - self.target_point.x, 0, actor_pos.z - self.target_point.z)
            if flat.length() < S.MISSION_RADIUS:
                self.money += S.MISSION_REWARD
                self.delivered += 1
                self.flash_message = f"Delivery complete! +${S.MISSION_REWARD}"
                self.flash_timer = 2.5
                self._spawn_marker()

        if self.flash_timer > 0:
            self.flash_timer -= time.dt
            if self.flash_timer <= 0:
                self.flash_message = ""

    @property
    def marker_world_pos(self):
        return self.target_point
