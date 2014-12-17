import random
import math
from intelligence import *


class BaseSimulationEntity:
    def __init__(self, x, y, energy):
        self.world = None
        self.x = x
        self.y = y
        self.energy = energy
        self.dead = False


class Bot(BaseSimulationEntity):
    counter = 0

    def __init__(self, x_start, y_start, energy, behavior_tree=None, name=None):
        super().__init__(x_start, y_start, energy)
        self.behavior_tree = behavior_tree
        self.speed = 1
        Bot.counter += 1
        if name is None:
            self.name = "Bot_" + str(Bot.counter)
        else:
            self.name = name

    def step(self):
        if self.behavior_tree is None:
            raise ValueError("Behavior Tree for bot %s must be BehaviorTree object, not None." % self)
        self.behavior_tree.step(self)
        self.energy -= 1
        if self.energy < 1:
            self.dead = True

    def __repr__(self):
        return self.name

    @staticmethod
    @statement
    def rest(bot):
        pass


class Plant(BaseSimulationEntity):
    counter = 0

    def __init__(self, x, y, energy, name=None):
        super().__init__(x, y, energy)
        Plant.counter += 1
        if name is None:
            self.name = "Plant_" + str(Plant.counter)
        else:
            self.name = name
        self.age = 0
        self.max_age = 1000
        self.max_energy = 200
        self.growth_rate = 1
        self.child_investment = 20
        self.spore_min_travel = 10
        self.spore_max_travel = 80
        self.percent_reproduction_chance = 2

    def step(self):
        # Check if the plant can grow
        if self.energy < self.max_energy:
            self.energy += self.growth_rate
        self.check_reproduction()
        # Check for death
        if self.age > self.max_age:
            self.dead = True
        self.age += 1

    def __repr__(self):
        return self.name

    def check_reproduction(self):
        if self.energy >= (self.max_energy - self.child_investment):
            # Check if reproduction randomly allowed
            if random.randint(0, 100) < self.percent_reproduction_chance:
                # Find the new location of the child
                travel_distance = random.randint(self.spore_min_travel, self.spore_max_travel)
                travel_angle_rads = random.random() * 2 * math.pi
                child_x = self.x + (travel_distance * math.sin(travel_angle_rads))
                child_y = self.y + (travel_distance * math.cos(travel_angle_rads))
                # Take energy from the parent and give to the child
                self.energy -= self.child_investment
                baby_plant = Plant(child_x, child_y, self.child_investment)
                self.world.add_plant(baby_plant)