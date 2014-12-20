import math
from intelligence import *
import numpy as np


class BaseSimulationEntity:
    def __init__(self, x, y, energy):
        self.name = 'entity'
        self.world = None
        self.x = x
        self.y = y
        self.energy = energy
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

    def __init__(self, x_start, y_start, energy, behavior_tree=None, name=None):
        super().__init__(x_start, y_start, energy)
        self.behavior_tree = behavior_tree
        self.speed = 1
        self.child_investment = 200
        self.target_point = None
        self.signal = None
        Bot.counter += 1
        if name is None:
            self.name = "Bot_" + str(Bot.counter)
        else:
            self.name = name

    def step(self):
        if self.behavior_tree is None:
            raise ValueError("Behavior Tree for bot %s must be BehaviorGraph object, not None." % self)
        if self.signal and self.signal.dead:
            self.signal = None
        self.behavior_tree.step(self)
        # Check if the bot has created a new signal
        if self.signal and self.signal not in self.world.signals:
            self.world.add_entity(self.signal)
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
        child = Bot(bot.x + np.random.random_integers(-3, 3), bot.y + np.random.random_integers(-3, 3), 0,
                    behavior_tree=bot.behavior_tree.return_tree_copy())
        child.behavior_tree.current_behavior_node = child.behavior_tree.behavior_nodes[0]
        bot.world.transfer_energy_between_entities(bot.child_investment, donor=bot, recipient=child)
        bot.number_children += 1
        # print("%s spawned %s" % (str(bot), str(child)))
        bot.world.add_entity(child)

    @staticmethod
    @statement
    def launch_signal(bot):
        bot.signal = MobileSignal(bot.x, bot.y, np.random.ranf()*2*math.pi, 0, bot)
        bot.world.transfer_energy_between_entities(10, donor=bot, recipient=bot.signal)

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
        if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
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
        unit_vector = bot.world.get_unit_vector_to_point((bot.x, bot.y), (bot.target_point[0], bot.target_point[1]))
        bot.x += unit_vector[0] * bot.speed
        bot.y += unit_vector[1] * bot.speed

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
        if bot.signal:
            bot.signal.dead = True
        bot.signal = StaticSignal(bot.x, bot.y, 0, bot)
        bot.world.transfer_energy_between_entities(3, donor=bot, recipient=bot.signal)
        bot.signal.step()
        if bot.signal.detected_objects:
            for entity in bot.signal.detected_objects:
                if isinstance(entity, Plant):
                    bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)
                    # message = "Transferring " + str(energy) + " energy to " + str(bot) + " from " + str(food)
                    # print(message)


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
                baby_plant = Plant(child_x, child_y, 0)
                self.world.transfer_energy_between_entities(self.child_investment, donor=self, recipient=baby_plant)
                self.number_children += 1
                self.world.add_entity(baby_plant)


class Signal(BaseSimulationEntity):
    counter = 0

    def __init__(self, x, y, energy, owner, name=None):
        super().__init__(x, y, energy)
        self.owner = owner
        self.world = owner.world
        self.detected_objects = []
        self.diameter = 8
        self.speed = 0
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
    def __init__(self, x, y, energy, owner, name=None):
        super().__init__(x, y, energy, owner, name)
        self.speed = 0
        self.diameter = 4

    def step(self):
        super().step()


class MobileSignal(Signal):
    def __init__(self, x, y, radians, energy, owner, name=None):
        super().__init__(x, y, energy, owner, name)
        self.speed = 2
        self.radians = radians
        self.x_diff = self.speed * math.cos(radians)
        self.y_diff = self.speed * math.sin(radians)

    def step(self):
        self.x += self.x_diff
        self.y += self.y_diff
        super().step()