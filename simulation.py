import functools
import copy
import random
import math
import os


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

    def execute(self, bot):
        if self.current_behavior_node is None:
            raise ValueError("Current Node Must be a function, not None.")
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

    def execute(self):
        if self.behavior_tree is None:
            raise ValueError("Behavior Tree for bot %s must be BehaviorTree object, not None." % self)
        self.behavior_tree.execute()


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

    def execute(self):
        # Check if the plant can grow
        if self.energy < self.max_energy:
            self.energy += self.growth_rate
        self.check_reproduction()
        # Check for death
        if self.age > self.max_age:
            self.dead = True
        self.age += 1

    def check_reproduction(self):
        if self.energy >= (self.max_energy - self.child_investment):
            # Check if reproduction randomly allowed
            if random.randint(0, 100) < self.percent_reproduction_chance:
                # Find the new location of the child
                travel_distance = random.randint(self.spore_min_travel, self.spore_max_travel)
                travel_angle_rads = random.random() * 2
                child_x = travel_distance * math.sin(travel_angle_rads)
                child_y = travel_distance * math.cos(travel_angle_rads)
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

    def execute(self):
        # Update plants
        for plant in list(self.plants):
            plant.execute()
            if plant.dead:
                self.plants.remove(plant)
        # Update bots
        for bot in list(self.bots):
            bot.execute()
            if bot.dead:
                self.bots.remove(bot)

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
    print("Starting Simulation...")
    Earth = World()
    Earth.add_plant(Plant(0, 0, 5))
    records = []
    for tick in range(1000):
        Earth.execute()
        print(len(Earth.plants), Earth.plants)
        records.append(len(Earth.plants))