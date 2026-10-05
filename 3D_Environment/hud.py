"""All screen-space UI: in-game HUD + minimap, the main menu and the pause menu."""

from ursina import Entity, Text, Button, color, camera, Vec2, application

import settings as S


# ------------------------------------------------------------------- HUD
class HUD:
    def __init__(self, mission, player):
        self.mission = mission
        self.player = player
        self.visible_help = False

        # --- health & stamina bars (top-left) ---
        self.health_bg = Entity(parent=camera.ui, model='quad', color=color.rgba32(0, 0, 0, 160),
                                 position=(-0.86, 0.46), scale=(0.26, 0.028), origin=(-0.5, 0))
        self.health_fill = Entity(parent=camera.ui, model='quad', color=color.rgb32(210, 50, 50),
                                   position=(-0.86, 0.46), scale=(0.26, 0.028), origin=(-0.5, 0))
        self.stamina_bg = Entity(parent=camera.ui, model='quad', color=color.rgba32(0, 0, 0, 160),
                                  position=(-0.86, 0.42), scale=(0.26, 0.018), origin=(-0.5, 0))
        self.stamina_fill = Entity(parent=camera.ui, model='quad', color=color.rgb32(60, 190, 100),
                                    position=(-0.86, 0.42), scale=(0.26, 0.018), origin=(-0.5, 0))

        # --- money & mission text (top) ---
        self.money_text = Text(parent=camera.ui, text='$0', position=(0.68, 0.46), scale=1.6,
                                color=color.gold)
        self.mission_text = Text(parent=camera.ui, text='Drive or walk to the gold marker',
                                  position=(0, 0.46), origin=(0, 0), scale=1.1, color=color.white)
        self.flash_text = Text(parent=camera.ui, text='', position=(0, 0.36), origin=(0, 0),
                                scale=1.4, color=color.lime)

        # --- speedometer (bottom-right, only while driving) ---
        self.speed_text = Text(parent=camera.ui, text='', position=(0.75, -0.42), scale=1.8,
                                color=color.white)

        # --- minimap (bottom-left) ---
        self.map_pos = Vec2(-0.72, -0.34)
        self.map_size = 0.28
        self.map_bg = Entity(parent=camera.ui, model='quad', color=color.rgba32(15, 15, 20, 200),
                              position=self.map_pos, scale=self.map_size)
        self.map_border = Entity(parent=camera.ui, model='quad', color=color.rgba32(255, 255, 255, 90),
                                  position=self.map_pos, scale=self.map_size + 0.01, z=0.01)
        self.map_bg.z = -0.005
        self.player_icon = Entity(parent=camera.ui, model='diamond', color=color.cyan,
                                   scale=(0.012, 0.024, 0.024), z=-0.02)
        self.marker_icon = Entity(parent=camera.ui, model='circle', color=color.gold, scale=0.016, z=-0.02)

        # --- controls help panel (toggle with H) ---
        self.help_panel = Entity(parent=camera.ui, model='quad', color=color.rgba32(0, 0, 0, 200),
                                  position=(0, 0), scale=(0.55, 0.42), enabled=False)
        self.help_text = Text(parent=self.help_panel, text='\n'.join(S.KEYBINDS_HELP), origin=(0, 0),
                               position=(0, 0), scale=1.3, color=color.white)

        self.hint_text = Text(parent=camera.ui, text='Press H for controls',
                               position=(0, -0.46), origin=(0, 0), scale=0.9, color=color.rgba32(255, 255, 255, 180))

    def toggle_help(self):
        self.visible_help = not self.visible_help
        self.help_panel.enabled = self.visible_help

    def update(self, city_span, driving_car):
        self.health_fill.scale_x = 0.26 * max(0, self.player.health / S.PLAYER_MAX_HEALTH)
        self.stamina_fill.scale_x = 0.26 * max(0, self.player.stamina / S.PLAYER_MAX_STAMINA)
        self.money_text.text = f"${self.mission.money}"
        self.flash_text.text = self.mission.flash_message

        if driving_car:
            kmh = abs(driving_car.speed) * 11.5
            self.speed_text.text = f"{kmh:0.0f} km/h"
        else:
            self.speed_text.text = ''

        actor = driving_car if driving_car else self.player
        scale = self.map_size / (city_span + 30)
        self.player_icon.position = self.map_pos + Vec2(actor.x * scale, actor.z * scale)
        self.player_icon.rotation_z = -actor.rotation_y

        target = self.mission.marker_world_pos
        self.marker_icon.position = self.map_pos + Vec2(target.x * scale, target.z * scale)


# -------------------------------------------------------------- main menu
class MainMenu:
    def __init__(self, on_play):
        self.on_play = on_play
        self.root = Entity(parent=camera.ui, enabled=True)

        Entity(parent=self.root, model='quad', color=color.rgba32(8, 10, 18, 235), scale=(3, 1.3))
        Text(parent=self.root, text='OPEN CITY', position=(0, 0.22), origin=(0, 0), scale=4,
             color=color.azure)
        Text(parent=self.root, text='an open-world Python adventure', position=(0, 0.12),
             origin=(0, 0), scale=1.2, color=color.rgba32(255, 255, 255, 180))

        Button(parent=self.root, text='Play', position=(0, -0.02), scale=(0.3, 0.08),
               color=color.rgb32(40, 130, 70), on_click=self._play)
        Button(parent=self.root, text='Controls', position=(0, -0.14), scale=(0.3, 0.08),
               color=color.rgb32(50, 70, 130), on_click=self._toggle_controls)
        Button(parent=self.root, text='Quit', position=(0, -0.26), scale=(0.3, 0.08),
               color=color.rgb32(150, 45, 45), on_click=application.quit)

        self.controls_text = Text(parent=self.root, text='\n'.join(S.KEYBINDS_HELP),
                                   position=(0, -0.4), origin=(0, 0), scale=1, enabled=False,
                                   color=color.white)

    def _toggle_controls(self):
        self.controls_text.enabled = not self.controls_text.enabled

    def _play(self):
        self.root.enabled = False
        self.on_play()

    def show(self):
        self.root.enabled = True


# ------------------------------------------------------------- pause menu
class PauseMenu:
    def __init__(self, on_resume, on_quit):
        self.on_resume = on_resume
        self.root = Entity(parent=camera.ui, enabled=False)

        Entity(parent=self.root, model='quad', color=color.rgba32(8, 10, 18, 220), scale=(1, 0.6))
        Text(parent=self.root, text='PAUSED', position=(0, 0.2), origin=(0, 0), scale=2.4,
             color=color.white)
        Button(parent=self.root, text='Resume', position=(0, 0.04), scale=(0.32, 0.08),
               color=color.rgb32(40, 130, 70), on_click=self._resume)
        Button(parent=self.root, text='Quit', position=(0, -0.08), scale=(0.32, 0.08),
               color=color.rgb32(150, 45, 45), on_click=on_quit)
        Text(parent=self.root, text='\n'.join(S.KEYBINDS_HELP), position=(0, -0.24),
             origin=(0, 0), scale=0.85, color=color.rgba32(255, 255, 255, 200))

    def _resume(self):
        self.on_resume()

    def set_visible(self, visible):
        self.root.enabled = visible
