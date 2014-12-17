import functools
import copy
import random
import math
import os
from matplotlib import pyplot as plt
import numpy as np
import time


class NodeRegister:
    # statement and conditional are just used to ID functions
    statement = 1
    conditional = 2
    registered_statements = []
    registered_conditionals = []


def statement(function):
    @functools.wraps(function)
    def dec(*args, **kwargs):
        return function(*args, **kwargs)

    NodeRegister.registered_statements.append(dec)
    return dec


def conditional(function):
    @functools.wraps(function)
    def dec(*args, **kwargs):
        return function(*args, **kwargs)

    NodeRegister.registered_conditionals.append(dec)
    return dec


class BehaviorNode:
    def __init__(self, function):
        self.function = function
        self.node_type = self._assign_node_type()
        self.next_node = None
        self.true_node = None
        self.false_node = None

    def execute(self, bot):
        result = self.function(bot)
        if self.node_type == NodeRegister.statement:
            return self.next_node
        elif self.node_type == NodeRegister.conditional:
            if result:
                return self.true_node
            return self.false_node

    def _assign_node_type(self):
        if self.function in NodeRegister.registered_statements:
            return NodeRegister.statement
        elif self.function in NodeRegister.registered_conditionals:
            return NodeRegister.conditional
        else:
            raise LookupError("Function %s is not registered as a statement or condition" % self.function)


class BehaviorTree:
    def __init__(self):
        self.behavior_nodes = []
        self.current_behavior_node = None

    def step(self, bot):
        if self.current_behavior_node is None:
            raise ValueError("Current Node Must be a function, not None. (Bot: %s)" % bot)
        self.current_behavior_node = self.current_behavior_node.execute(bot)

    def return_tree_copy(self):
        return copy.deepcopy(self)

    def generate_random_tree(self):
        pass


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


class World:
    def __init__(self, bot_limit=None, plant_limit=None):
        self.bots = []
        self.plants = []
        self.bot_limit = bot_limit
        self.plant_limit = plant_limit

    def step(self):
        # Update all plants then all bots
        for array in [self.plants, self.bots]:
            for entity in list(array):
                entity.step()
                if entity.dead:
                    array.remove(entity)

    def add_bot(self, bot):
        if self.bot_limit and len(self.bot_limit) > self.bot_limit:
            return False
        bot.world = self
        self.bots.append(bot)

    def add_plant(self, plant):
        if self.plant_limit and len(self.plants) > self.plant_limit:
            return False
        plant.world = self
        self.plants.append(plant)


if __name__ == '__main__':
    start_time = time.time()
    print("Starting Simulation...")
    Earth = World(plant_limit=2000)
    Earth.add_plant(Plant(0, 0, 5))
    plant_numbers = []
    bot_numbers = []

    def run(ticks):
        for tick in range(ticks):
            Earth.step()
            # Keep track of some info for graphing
            plant_numbers.append(len(Earth.plants))
            bot_numbers.append(len(Earth.bots))

    run(750)
    basic_behavior = BehaviorTree()
    basic_node = BehaviorNode(Bot.rest)
    basic_node.next_node = basic_node
    basic_behavior.behavior_nodes = [basic_node]
    basic_behavior.current_behavior_node = basic_behavior.behavior_nodes[0]
    for i in range(50):
        Earth.add_bot(Bot(random.randint(-50, 50), random.randint(-50, 50), 200,
                          behavior_tree=basic_behavior.return_tree_copy()))
    run(750)

    # Create some graphs to get a sense of what's going on
    graph = plt.figure()
    graph.subplots_adjust(wspace=0.4)
    graph.subplots_adjust(hspace=0.4)
    plant_dist = graph.add_subplot(2, 2, 1)
    plant_dist.scatter([plant.x for plant in Earth.plants], [plant.y for plant in Earth.plants], s=2, lw=0)
    plant_dist.set_xlabel('X')
    plant_dist.set_ylabel('Y')

    plant_nums = graph.add_subplot(2, 2, 2)
    plant_nums.set_xlabel('Time')
    plant_nums.set_ylabel('Number of Plants')
    plant_nums.plot(range(0, len(plant_numbers)), plant_numbers)

    bot_dist = graph.add_subplot(2, 2, 3)
    bot_dist.scatter([bot.x for bot in Earth.bots], [bot.y for bot in Earth.bots], s=2, lw=0)
    bot_dist.set_xlabel('X')
    bot_dist.set_ylabel('Y')

    bot_nums = graph.add_subplot(2, 2, 4)
    bot_nums.plot(range(0, len(bot_numbers)), bot_numbers,)
    bot_nums.set_xlabel('Time')
    bot_nums.set_ylabel('Number of Bots')

    # Make all subplot axes tick labels smaller and give them a title
    for subplot, title in [(plant_dist, 'Plant Distribution'), (plant_nums, 'Plant Numbers'),
                           (bot_dist, 'Bot Distribution'), (bot_nums, 'Bot Numbers')]:
        subplot.tick_params(labelsize=6)
        subplot.set_title(title)

    graph.savefig(os.getcwd() + os.sep + 'graphs' + os.sep + 'simulation.png', dpi=100)
    print("Elapsed seconds:", time.time() - start_time)