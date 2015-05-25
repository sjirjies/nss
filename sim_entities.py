import math
from intelligence import *
import numpy as np


class BaseSimulationEntity:
    def __init__(self, x, y):
        self.name = 'entity'
        self.world = None
        self.x = x
        self.y = y
        self.energy = 0
        self.dead = False
        self.birthday = None
        self.age = 0
        self.number_children = 0

    def step(self):
        self.age += 1
        self.world.drain_energy_from_entity(1, self)
        if self.energy < 1:
            self.dead = True

    def __str__(self):
        return self.name


class Bot(BaseSimulationEntity):
    counter = 0

    def __init__(self, x_start, y_start, generation_number=-1, behavior_graph=None, name=None):
        super().__init__(x_start, y_start)
        self.behavior = behavior_graph
        self.speed = 1
        self.child_investment = 200
        self.max_age = 2000
        self.peak_energy = 0
        self.generation_number = generation_number
        self.target_point = x_start, y_start
        self.signal = None
        Bot.counter += 1
        if name is None:
            self.name = "Bot_" + str(Bot.counter)
        else:
            self.name = name

    def step(self):
        if self.behavior is None:
            raise ValueError("Behavior Tree for %s must be BehaviorGraph object, not None." % self)
        if self.signal and self.signal.dead:
            self.signal = None
        self.behavior.step(self)
        # Check if the bot has created a new signal
        if self.signal and self.signal not in self.world.signals:
            self.world.add_entity(self.signal)
        super().step()
        if self.age >= self.max_age:
            self.dead = True
        if self.energy > self.peak_energy:
            self.peak_energy = self.energy


class Plant(BaseSimulationEntity):
    counter = 0

    def __init__(self, x, y, name=None):
        super().__init__(x, y)
        Plant.counter += 1
        if name is None:
            self.name = "Plant_" + str(Plant.counter)
        else:
            self.name = name
        self.age = 0
        self.max_age = 1000
        self.max_energy = 200
        self.growth_rate = 2
        self.child_investment = 100
        self.spore_min_travel = 10
        self.spore_max_travel = 80
        self.percent_reproduction_chance = 2

    def step(self):
        # Check if the plant can grow
        if self.energy < self.max_energy:
            self.world.give_energy_to_entity(self.growth_rate, self)
        self.check_reproduction()
        # Check for death
        if self.age > self.max_age:
            self.dead = True
        self.age += 1

    def check_reproduction(self):
        if self.energy >= (self.max_energy - self.child_investment):
            # Check if reproduction randomly allowed
            if np.random.random_integers(0, 100) < self.percent_reproduction_chance:
                # Find the new location of the child
                travel_distance = np.random.random_integers(self.spore_min_travel, self.spore_max_travel)
                travel_angle_rads = np.random.ranf() * 2 * math.pi
                child_x = self.x + (travel_distance * math.sin(travel_angle_rads))
                child_y = self.y + (travel_distance * math.cos(travel_angle_rads))
                # Create a baby plant and give it energy from the parent
                baby_plant = Plant(child_x, child_y)
                self.world.transfer_energy_between_entities(self.child_investment, donor=self, recipient=baby_plant)
                self.number_children += 1
                self.world.add_entity(baby_plant)


class Signal(BaseSimulationEntity):
    counter = 0

    def __init__(self, x, y, owner, name=None, color=None):
        super().__init__(x, y)
        self.owner = owner
        self.origination_pos = owner.x, owner.y
        self.world = owner.world
        self.detected_objects = []
        self.diameter = 8
        self.speed = 0
        self.color = color
        Signal.counter += 1
        if name:
            self.name = name
        else:
            self.name = 'Signal_' + str(Signal.counter)

    def step(self):
        self.detected_objects = []
        if self.world.kd_tree:
            # Note: KDTree lookup always returns the signal object as the closest point
            indexes = self.world.kd_tree.query_ball_point((np.array((self.x, self.y))), r=self.diameter//2)
            for index in indexes:
                entity = self.world.all_entities[index]
                if entity not in self.detected_objects:
                    self.detected_objects.append(entity)
        super().step()

    def __str__(self):
        return self.name


# TODO: Ingest Static and Mobile Signal into Signal. Let Bots toggle the speed and other properies.
class StaticSignal(Signal):
    def __init__(self, x, y, owner, name=None, color=None):
        super().__init__(x, y, owner, name, color)
        self.speed = 0
        self.diameter = 4

    def step(self):
        super().step()


class MobileSignal(Signal):
    def __init__(self, x, y, radians, owner, name=None, color=None):
        super().__init__(x, y, owner, name, color)
        self.speed = 2
        self.radians = radians
        self.x_diff = self.speed * math.cos(radians)
        self.y_diff = self.speed * math.sin(radians)

    def step(self):
        self.x += self.x_diff
        self.y += self.y_diff
        super().step()