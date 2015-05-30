from intelligence import statement, conditional
from sim_entities import Plant, Bot, MobileSignal, StaticSignal, Signal

from numpy.random import random_integers, ranf
import math

##########################################
# These functions are provided by default.
##########################################

@conditional
def reproduce_possible(bot):
    if bot.energy > bot.child_investment:
        return True
    return False

@statement
def create_clone(bot):
    # Let's require the bot to have energy before it can do this
    if bot.energy > 0:
        # First the parent bot must pay an energy tax
        bot.world.drain_energy_from_entity(5, bot)
        child_behavior = bot.behavior.return_tree_copy()
        # If is the second or greater child, then possible mutate the behavior
        if bot.number_children >= 2:
            if random_integers(1, 100) < 85:
                child_behavior.mutate_behavior()
        child = Bot(bot.x + random_integers(-3, 3), bot.y + random_integers(-3, 3),
                    generation_number=bot.generation_number+1, behavior_graph=child_behavior)
        # For now just start at the first node. Setting it to a random one could be interesting as well.
        child.behavior.set_entry_node(child.behavior.behavior_nodes[0])
        bot.world.transfer_energy_between_entities(bot.child_investment, donor=bot, recipient=child)
        bot.number_children += 1
        # print("%s spawned %s" % (str(bot), str(child)))
        bot.world.add_entity(child)

@statement
def launch_signal(bot):
    # TODO: Make signal creation not require passing 0 and setting energy with a World method
    bot.signal = MobileSignal(bot.x, bot.y, ranf()*2*math.pi, bot, color=(60, 60, 190))
    bot.world.transfer_energy_between_entities(10, donor=bot, recipient=bot.signal)

@conditional
def signal_exists(bot):
    if bot.signal:
        return True
    return False

@statement
def wait(bot):
    pass

@conditional
def has_signal_found_plant(bot):
    if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
        for item in bot.signal.detected_objects:
            # TODO: get rid of isinstance and use something better
            if isinstance(item, Plant):
                # print("FOUND FOOD %s at %d, %d" % (item, item.x, item.y))
                bot.target_point = item.x, item.y
                return True
    return False

@statement
def move_towards_target(bot):
    if bot.target_point:
        unit_vector = bot.world.get_unit_vector_to_point((bot.x, bot.y), (bot.target_point[0], bot.target_point[1]))
        bot.x += unit_vector[0] * bot.speed
        bot.y += unit_vector[1] * bot.speed

@conditional
def target_nearby(bot):
    if bot.target_point:
        if math.sqrt(((bot.target_point[0] - bot.x)**2) + ((bot.target_point[1] - bot.y)**2)) <= 2:
            return True
    return False

@statement
def eat_nearby_plants(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(120, 240, 130))
    bot.signal.diameter = 6
    bot.world.transfer_energy_between_entities(3, donor=bot, recipient=bot.signal)
    bot.signal.step()
    if bot.signal.detected_objects:
        for entity in bot.signal.detected_objects:
            if isinstance(entity, Plant):
                bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)

#######################################################
# The functions below are extra. Feel free to add more.
#######################################################

@statement
def create_local_signal(bot):
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(40, 40, 180))
    bot.signal.diameter = 24
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)


@statement
def create_long_range_signal(bot):
    # TODO: Allow bots to store a direction for their signal propagation instead of using a random one
    bot.signal = MobileSignal(bot.x, bot.y, ranf()*2*math.pi, bot, color=(150, 190, 240))
    bot.signal.diameter = 4
    bot.world.transfer_energy_between_entities(25, donor=bot, recipient=bot.signal)


@statement
def set_random_target(bot):
    bot.target_point = bot.x + random_integers(-100, 100), bot.y + random_integers(-100, 100)


@statement
def eat_nearby_bots(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(240, 90, 90))
    bot.signal.diameter = 6
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)
    bot.signal.step()
    if bot.signal.detected_objects:
        for entity in bot.signal.detected_objects:
            if isinstance(entity, Bot) and entity is not bot:
                bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)


@conditional
def has_signal_found_bots(bot):
    if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
        for item in bot.signal.detected_objects:
            if isinstance(item, Bot):
                # print("FOUND FOOD %s at %d, %d" % (item, item.x, item.y))
                bot.target_point = item.x, item.y
                return True
    return False


@conditional
def has_signal_found_signal(bot):
    if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
        for item in bot.signal.detected_objects:
            if isinstance(item, Bot) and item is not bot.signal:
                # print("FOUND FOOD %s at %d, %d" % (item, item.x, item.y))
                bot.target_point = item.x, item.y
                return True
    return False


@statement
def eat_nearby_signal(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(130, 130, 230))
    bot.signal.diameter = 6
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)
    bot.signal.step()
    if bot.signal.detected_objects:
        for entity in bot.signal.detected_objects:
            if isinstance(entity, Signal) and entity is not bot.signal:
                bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)

@statement
def create_sniper_signal(bot):
    # TODO: Allow bots to store a direction for their signal propagation instead of using a random one
    bot.signal = MobileSignal(bot.x, bot.y, ranf()*2*math.pi, bot, color=(190, 220, 240))
    bot.signal.diameter = 2
    bot.world.transfer_energy_between_entities(50, donor=bot, recipient=bot.signal)

@conditional
def random_choice(bot):
    return random_integers(0, 1)

@conditional
def very_low_energy(bot):
    if bot.energy < 100:
        return True
    return False

@statement
def set_target_to_signal_origin(bot):
    if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
        for item in bot.signal.detected_objects:
            if isinstance(item, Signal) and item is not bot.signal:
                bot.target_point = item.x, item.y
                return True
    return False

