import math
from random import randint, random

import tkinter as tk

from gamelib import Sprite, GameApp, Text, KeyboardHandler, StatusWithText

from consts import *
from elements import Ship, Bullet, Enemy
from utils import random_edge_position, normalize_vector, direction_to_dxdy, vector_len, distance

from abc import ABC, abstractmethod

### start strategy pattern ###
class EnemyGenerationStrategy(ABC):
    @abstractmethod
    def generate(self, space_game, ship):
        pass

class StarEnemyGenerationStrategy(EnemyGenerationStrategy):
    def generate(self, space_game, ship):
        ####
        # TODO: extracted from method create_enemy_star
        enemies = []

        x = randint(100, CANVAS_WIDTH - 100)
        y = randint(100, CANVAS_HEIGHT - 100)

        while vector_len(x - ship.x, y - ship.y) < 200:
            x = randint(100, CANVAS_WIDTH - 100)
            y = randint(100, CANVAS_HEIGHT - 100)

        for d in range(18):
            dx, dy = direction_to_dxdy(d * 20)
            enemy = Enemy(space_game, x, y, dx * ENEMY_BASE_SPEED, dy * ENEMY_BASE_SPEED)
            enemies.append(enemy)

        return enemies

class EdgeEnemyGenerationStrategy(EnemyGenerationStrategy):
    def generate(self, space_game, ship):
        ####
        # TODO: extracted from method create_enemy_from_edge
        x, y = random_edge_position()
        vx, vy = normalize_vector(ship.x - x, ship.y - y)

        vx *= ENEMY_BASE_SPEED
        vy *= ENEMY_BASE_SPEED

        enemy = Enemy(space_game, x, y, vx, vy)
        return [enemy]
### end strategy pattern ###

### START: CoR pattern ###
class GameKeyboardHandler(KeyboardHandler):
    def __init__(self, game_app, ship, successor=None):
        super().__init__(successor)
        self.game_app = game_app
        self.ship = ship

class BombKeyPressedHandler(GameKeyboardHandler):
    def handle(self, event):
        if event.char.upper() == 'Z':
            self.game_app.bomb()
        else:                                     #
            super().handle(event)

class ShipMovementKeyPressedHandler(GameKeyboardHandler):
    def handle(self, event):
        # TODO:
        #   - extract the code from on_key_pressed
        if event.keysym == 'Left':
            self.ship.start_turn('LEFT')
        elif event.keysym == 'Right':
            self.ship.start_turn('RIGHT')
        elif event.char == ' ':
            self.ship.fire()
        else:
            super().handle(event)

class ShipMovementKeyReleasedHandler(GameKeyboardHandler):
    def handle(self, event):
        # TODO:
        #   - extract the code from on_key_released
        if event.keysym == 'Left':
            self.ship.stop_turn('LEFT')
        elif event.keysym == 'Right':
            self.ship.stop_turn('RIGHT')
        else:
            super().handle(event)
### END: CoR pattern ###


class SpaceGame(GameApp):
    def init_game(self):
        self.ship = Ship(self, CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)

        self.level = StatusWithText(self, 100, 580, 'Level: %d', 1)

        # StatusWithText encap
        self.score = StatusWithText(self, 100, 20, 'Score: %d', 0)
        self.score_wait = 0
        
        self.bomb_power = StatusWithText(self, 700, 20, 'Power: %d%%', BOMB_FULL_POWER)
        self.bomb_wait = 0

        self.elements.append(self.ship)

        self.enemies = []
        self.bullets = []

        # strategy pattern
        self.enemy_creation_strategies = [
            (0.2, StarEnemyGenerationStrategy()),
            (1.0, EdgeEnemyGenerationStrategy())
        ]

        # CoR pattern
        self.init_key_handlers()

        # canvas configure
        self.canvas.configure(bg="darkgray")
        for item in [self.level, self.score, self.bomb_power]:
            self.canvas.itemconfigure(item.label_text.canvas_object_id, fill="white")

    def add_enemy(self, enemy):
        self.enemies.append(enemy)

    def add_bullet(self, bullet):
        self.bullets.append(bullet)

    def bullet_count(self):
        return len(self.bullets)

    def bomb(self):
        if self.bomb_power.value == BOMB_FULL_POWER:
            self.bomb_power.value = 0

            self.bomb_canvas_id = self.canvas.create_oval(
                self.ship.x - BOMB_RADIUS, 
                self.ship.y - BOMB_RADIUS,
                self.ship.x + BOMB_RADIUS, 
                self.ship.y + BOMB_RADIUS
            )

            self.after(200, lambda: self.canvas.delete(self.bomb_canvas_id))

            for e in self.enemies:
                if self.ship.distance_to(e) <= BOMB_RADIUS:
                    e.to_be_deleted = True

    def update_score(self):
        self.score_wait += 1
        if self.score_wait >= SCORE_WAIT:
            self.score.value += 1
            self.score_wait = 0

    def update_bomb_power(self):
        self.bomb_wait += 1
        if (self.bomb_wait >= BOMB_WAIT) and (self.bomb_power.value != BOMB_FULL_POWER):
            self.bomb_power.value += 1
            self.bomb_wait = 0

    def update_level(self):
        pass
        
    def create_enemies(self):
        p = random()

        for prob, strategy in self.enemy_creation_strategies:
            if p < prob:
                enemies = strategy.generate(self, self.ship)
                break

        for e in enemies:
            self.add_enemy(e)

    def pre_update(self):
        if random() < 0.1:
            self.create_enemies()

    def process_bullet_enemy_collisions(self):
        for b in self.bullets:
            for e in self.enemies:
                if b.is_colliding_with_enemy(e):
                    b.to_be_deleted = True
                    e.to_be_deleted = True

    def process_ship_enemy_collision(self):
        for e in self.enemies:
            if self.ship.is_colliding_with_enemy(e):
                self.stop_animation()

    def process_collisions(self):
        self.process_bullet_enemy_collisions()
        self.process_ship_enemy_collision()

    def update_and_filter_deleted(self, elements):
        new_list = []
        for e in elements:
            e.update()
            e.render()
            if e.to_be_deleted:
                e.delete()
            else:
                new_list.append(e)
        return new_list

    def post_update(self):
        self.process_collisions()

        self.bullets = self.update_and_filter_deleted(self.bullets)
        self.enemies = self.update_and_filter_deleted(self.enemies)

        self.update_score()
        self.update_bomb_power()
    
    # CoR pattern
    def init_key_handlers(self):
        key_pressed_handler = ShipMovementKeyPressedHandler(self, self.ship)
        key_pressed_handler = BombKeyPressedHandler(self, self.ship, key_pressed_handler)
        self.key_pressed_handler = key_pressed_handler

        key_released_handler = ShipMovementKeyReleasedHandler(self, self.ship)
        self.key_released_handler = key_released_handler


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Space Fighter")
 
    # do not allow window resizing
    root.resizable(False, False)
    app = SpaceGame(root, CANVAS_WIDTH, CANVAS_HEIGHT, UPDATE_DELAY)
    app.start()
    root.mainloop()
