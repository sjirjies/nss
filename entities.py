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
        self.energy -= 1
        if self.energy < 1:
            self.dead = True

    def __repr__(self):
        return self.name


class Bot(BaseSimulationEntity):
    counter = 0

    def __init__(self, x_start, y_start, energy, behavior_tree=None, name=None):
        super().__init__(x_start, y_start, energy)
        self.behavior_tree = behavior_tree
        self.speed = 1
        self.child_investment = 200
        self.max_energy = 400
        self.target_point = None
        self.signal = None
        Bot.counter += 1
        if name is None:
            self.name = "Bot_" + str(Bot.counter)
        else:
            self.name = name

    def step(self):
        if self.behavior_tree is None:
            raise ValueError("Behavior Tree for bot %s must be BehaviorTree object, not None." % self)
        if self.signal and self.signal.dead:
            self.signal = None
        self.behavior_tree.step(self)
        if self.signal and self.signal not in self.world.signals:
            self.world.signals.append(self.signal)
        super().step()

    @staticmethod
    @conditional
    def can_i_reproduce(bot):
        if bot.energy > bot.child_investment:
            return True
        return False

    @staticmethod
    @statement
    def create_clone(bot):
        child = Bot(bot.x + random.randint(-3, 3), bot.y + random.randint(-3, 3),
                    bot.child_investment, behavior_tree=bot.behavior_tree.return_tree_copy())
        child.behavior_tree.current_behavior_node = child.behavior_tree.behavior_nodes[0]
        bot.energy -= bot.child_investment
        # print("%s spawned %s" % (str(bot), str(child)))
        bot.world.add_bot(child)

    @staticmethod
    @statement
    def launch_signal(bot):
        bot.signal = MobileSignal(bot.x, bot.y, random.random()*2*math.pi, 10, bot)

    @staticmethod
    @conditional
    def do_i_have_a_signal(bot):
        if bot.signal:
            return True
        return False

    @staticmethod
    @statement
    def wait(bot):
        pass

    @staticmethod
    @conditional
    def has_signal_found_food(bot):
        if bot.signal and bot.signal.detected_objects and bot.signal.energy > 2:
            for item in bot.signal.detected_objects:
                # TODO: get rid of isinstance and use something better
                if isinstance(item, Plant):
                    # print("FOUND FOOD %s at %d, %d" % (item, item.x, item.y))
                    bot.target_point = item.x, item.y
                    return True
        return False

    @staticmethod
    @statement
    def move_towards_target(bot):
        if bot.target_point:
            x, y = bot.target_point[0] - bot.x, bot.target_point[1] - bot.y
            distance = math.sqrt((x**2) + (y**2))
            if distance > 0:
                bot.x += x/distance * bot.speed
                bot.y += y/distance * bot.speed

    @staticmethod
    @conditional
    def am_i_near_target(bot):
        if bot.target_point:
            if math.sqrt(((bot.target_point[0] - bot.x)**2) + ((bot.target_point[1] - bot.y)**2)) <= 2:
                return True
        return False

    @staticmethod
    @statement
    def eat_nearby_food(bot):
        # TODO: have bots use signals to find food within a small distance from them
        if bot.energy < bot.max_energy:
            for food in bot.world.plants:
                if math.sqrt(((food.x - bot.x)**2) + ((food.y - bot.y)**2)) <= 4:
                    energy = food.energy
                    food.energy = 0
                    food.dead = True
                    bot.energy += energy
                    # message = "Transferring " + str(energy) + " energy to " + str(bot) + " from " + str(food)
                    # print(message)
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
        self.max_energy = 200
        self.growth_rate = 2
        self.child_investment = 100
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


class Signal(BaseSimulationEntity):
    counter = 0

    def __init__(self, x, y, energy, owner, name=None):
        super().__init__(x, y, energy)
        self.owner = owner
        self.world = owner.world
        self.detected_objects = []
        self.diameter = 8
        self.speed = 2
        Signal.counter += 1
        if name:
            self.name = name
        else:
            self.name = 'Signal_' + str(Signal.counter)

    def __repr__(self):
        return self.name


class StaticSignal(Signal):
    def __init__(self, x, y, energy, owner, name=None):
        super().__init__(x, y, energy, owner, name)

    def step(self):
        # TODO: Have the signal query the world for information
        super().step()


class MobileSignal(Signal):
    def __init__(self, x, y, radians, energy, owner, name=None):
        super().__init__(x, y, energy, owner, name)
        self.radians = radians
        self.x_diff = self.speed * math.cos(radians)
        self.y_diff = self.speed * math.sin(radians)

    def step(self):
        self.x += self.x_diff
        self.y += self.y_diff
        # TODO: Replace this with something better, like a KD-Tree
        # self.detected_objects = []
        for entity_list in self.owner.world.bots, self.owner.world.plants:
            for item in entity_list:
                if math.sqrt(((item.x - self.x)**2) + ((item.y - self.y)**2)) <= self.diameter/2:
                    if item not in self.detected_objects:
                        self.detected_objects.append(item)
        super().step()