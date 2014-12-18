import random
import math
from intelligence import *


class BaseSimulationEntity:
    def __init__(self, x, y, energy):
        self.name = 'BaseEntity'
        self.world = None
        self.x = x
        self.y = y
        self.energy = energy
        self.dead = False

    def step(self):
        pass

    def __repr__(self):
        return self.name


class Bot(BaseSimulationEntity):
    counter = 0

    def __init__(self, x_start, y_start, energy, behavior_tree=None, name=None):
        super().__init__(x_start, y_start, energy)
        self.behavior_tree = behavior_tree
        self.speed = 1
        self.child_investment = 200
        self.max_energy = 300
        self.target_point = None
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

    @staticmethod
    @conditional
    def can_i_reproduce(bot):
        if bot.energy > bot.child_investment:
            return True
        return False

    @staticmethod
    @statement
    def create_clone(bot):
        child = Bot(bot.x + random.randint(-10, 10), bot.y + random.randint(-10, 10),
                    bot.child_investment, behavior_tree=bot.behavior_tree.return_tree_copy())
        child.behavior_tree.current_behavior_node = child.behavior_tree.behavior_nodes[0]
        print("%s spawned %s" % (str(bot), str(child)))
        bot.world.add_bot(child)

    @staticmethod
    @statement
    def target_food(bot):
        # TODO: switch to using signals to find distant location of food
        arbitrary_plant = bot.world.plants[0]
        bot.target_point = arbitrary_plant.x, arbitrary_plant.y

    @staticmethod
    @statement
    def move_towards_target(bot):
        x, y = bot.target_point[0] - bot.x, bot.target_point[1] - bot.y
        distance = math.sqrt((x**2) + (y**2))
        if distance > 0:
            bot.x += x/float(distance)
            bot.y += y/float(distance)

    @staticmethod
    @conditional
    def am_i_near_target(bot):
        if math.sqrt(((bot.target_point[0] - bot.x)**2) + ((bot.target_point[1] - bot.y)**2)) <= 2:
            return True
        return False

    @staticmethod
    @statement
    def eat_nearby_food(bot):
        # TODO: have bots use signals to find food within a small distance from them
        if bot.energy < bot.max_energy:
                for food in bot.world.plants:
                    if math.sqrt(((food.x - bot.x)**2) + ((food.y - bot.y)**2)) <= 3:
                        message = "Transferring "
                        energy = food.energy
                        message += str(energy) + " energy from " + str(food) + " to " + str(bot)
                        food.world.plants.remove(food)
                        bot.energy += energy
                        print(message)
                    break


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
        self.max_energy = 50
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