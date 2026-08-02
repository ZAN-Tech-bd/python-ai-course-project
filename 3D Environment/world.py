"""Procedural open-world city: ground, roads, buildings, streetlights and
the waypoint loops that pedestrians/traffic follow."""

import random
from ursina import Entity, Vec3, color, destroy

import settings as S


def _grid_lines():
    """World-space positions of the N+1 road centerlines on one axis."""
    return [i * S.PITCH - S.HALF_CITY for i in range(S.BLOCKS_PER_SIDE + 1)]


class City:
    def __init__(self):
        self.buildings = []       # list of dicts: {entity, x, z, half}
        self.streetlights = []
        self.pedestrian_loops = []
        self.traffic_loops = []
        self.entities = []        # everything spawned, for cleanup

        self._build_ground()
        self._build_roads()
        self._build_buildings()
        self._build_streetlights()
        self._build_props()
        self._build_paths()

    # ---------------------------------------------------------- ground
    def _build_ground(self):
        ground = Entity(
            model='plane',
            scale=(S.CITY_SPAN + 40, 1, S.CITY_SPAN + 40),
            texture='white_cube',
            texture_scale=(S.CITY_SPAN / 2, S.CITY_SPAN / 2),
            color=color.rgb32(120, 122, 118),
            collider='box',
            name='ground',
        )
        self.entities.append(ground)

        # a couple of grass parks for variety / color contrast
        lines = _grid_lines()
        for _ in range(3):
            i = random.randrange(len(lines) - 1)
            j = random.randrange(len(lines) - 1)
            cx = lines[i] + S.PITCH / 2
            cz = lines[j] + S.PITCH / 2
            park = Entity(
                model='plane',
                position=(cx, 0.02, cz),
                scale=(S.BLOCK_SIZE - 2, 1, S.BLOCK_SIZE - 2),
                texture='grass',
                texture_scale=(6, 6),
                color=color.rgb32(70, 130, 70),
            )
            self.entities.append(park)

    # ------------------------------------------------------------ roads
    def _build_roads(self):
        lines = _grid_lines()
        span = S.CITY_SPAN + S.ROAD_WIDTH
        road_render_width = S.ROAD_WIDTH - S.SIDEWALK_MARGIN

        for pos in lines:
            # road running along Z (constant x)
            road_x = Entity(
                model='cube',
                position=(pos, 0.01, 0),
                scale=(road_render_width, 0.05, span),
                color=color.rgb32(35, 35, 38),
            )
            # road running along X (constant z)
            road_z = Entity(
                model='cube',
                position=(0, 0.01, pos),
                scale=(span, 0.05, road_render_width),
                color=color.rgb32(35, 35, 38),
            )
            self.entities += [road_x, road_z]

            # dashed centerline markings
            for t in range(-int(span // 2), int(span // 2), 6):
                dash_x = Entity(model='cube', position=(pos, 0.02, t),
                                 scale=(0.3, 0.06, 2), color=color.yellow)
                dash_z = Entity(model='cube', position=(t, 0.02, pos),
                                 scale=(2, 0.06, 0.3), color=color.yellow)
                self.entities += [dash_x, dash_z]

    # -------------------------------------------------------- buildings
    def _build_buildings(self):
        lines = _grid_lines()
        for i in range(S.BLOCKS_PER_SIDE):
            for j in range(S.BLOCKS_PER_SIDE):
                cx = lines[i] + S.PITCH / 2
                cz = lines[j] + S.PITCH / 2
                footprint = S.BLOCK_SIZE - 4  # leaves sidewalk margin
                height = random.uniform(6, 42)
                tint = random.choice(S.BUILDING_PALETTE)
                tex = random.choice(['white_cube', 'brick'])

                building = Entity(
                    model='cube',
                    position=(cx, height / 2, cz),
                    scale=(footprint, height, footprint),
                    texture=tex,
                    texture_scale=(footprint / 2, height / 2),
                    color=color.rgb32(*[int(c * 255) for c in tint]),
                    collider='box',
                    name='building',
                )
                # flat roof cap for a cleaner skyline silhouette
                roof = Entity(
                    model='cube',
                    position=(cx, height + 0.05, cz),
                    scale=(footprint * 1.02, 0.1, footprint * 1.02),
                    color=color.rgb32(25, 25, 28),
                )
                self.entities += [building, roof]
                self.buildings.append({
                    'entity': building, 'x': cx, 'z': cz, 'half': footprint / 2
                })

    # ------------------------------------------------------ streetlights
    def _build_streetlights(self):
        lines = _grid_lines()
        for x in lines:
            for z in lines:
                if random.random() < 0.6:
                    continue  # skip most intersections to avoid clutter
                pole = Entity(model='cube', position=(x + 2, 2, z + 2),
                               scale=(0.15, 4, 0.15), color=color.rgb32(40, 40, 40))
                lamp = Entity(model='sphere', position=(x + 2, 4, z + 2),
                               scale=0.4, color=color.rgb32(255, 235, 180))
                self.entities += [pole, lamp]
                self.streetlights.append(lamp)

    # -------------------------------------------------------------- props
    def _build_props(self):
        # a handful of decorative parked cars along the curb for atmosphere
        lines = _grid_lines()
        for _ in range(10):
            x = random.choice(lines) + random.choice([-S.SIDEWALK_MARGIN - 1, S.SIDEWALK_MARGIN + 1])
            z = random.uniform(-S.HALF_CITY, S.HALF_CITY)
            car = Entity(
                model='cube',
                position=(x, 0.4, z),
                scale=(1.7, 0.8, 3.4),
                color=color.rgb32(*random.choice([(180, 30, 30), (30, 60, 180), (200, 200, 200), (40, 40, 40)])),
            )
            self.entities.append(car)

    # -------------------------------------------------------------- paths
    def _build_paths(self):
        """Rectangular waypoint loops used by traffic cars (road centerlines)
        and pedestrians (sidewalk ring just outside a block)."""
        lines = _grid_lines()

        # outer perimeter loop for traffic
        outer = lines[0]
        far = lines[-1]
        self.traffic_loops.append([
            Vec3(outer, 0.4, outer), Vec3(far, 0.4, outer),
            Vec3(far, 0.4, far), Vec3(outer, 0.4, far),
        ])
        # a couple of inner loops using interior grid lines
        mid = len(lines) // 2
        if S.BLOCKS_PER_SIDE >= 3:
            a, b = lines[1], lines[mid]
            self.traffic_loops.append([
                Vec3(a, 0.4, a), Vec3(b, 0.4, a), Vec3(b, 0.4, b), Vec3(a, 0.4, b),
            ])

        # pedestrian sidewalk loops: ring around each of a few random blocks
        blocks = random.sample(self.buildings, min(6, len(self.buildings)))
        for b in blocks:
            r = b['half'] + 1.6
            cx, cz = b['x'], b['z']
            self.pedestrian_loops.append([
                Vec3(cx - r, 0, cz - r), Vec3(cx + r, 0, cz - r),
                Vec3(cx + r, 0, cz + r), Vec3(cx - r, 0, cz + r),
            ])

    # ---------------------------------------------------------------
    def random_road_point(self):
        """A random point that sits on a road (safe for cars/missions)."""
        lines = _grid_lines()
        if random.random() < 0.5:
            x = random.choice(lines)
            z = random.uniform(-S.HALF_CITY, S.HALF_CITY)
        else:
            z = random.choice(lines)
            x = random.uniform(-S.HALF_CITY, S.HALF_CITY)
        return Vec3(x, 0, z)
