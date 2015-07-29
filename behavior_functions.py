from intelligence import statement, conditional
from sim_entities import Plant, Bot, MobileSignal, StaticSignal, Signal

from numpy.random import random_integers, ranf
import math

##########################################
# These functions are provided by default.
# Still feel free to modify them
##########################################

# TODO: Include a decorator for comparing two bots for champion selection

def _check_detected_entity_type(signal, entity_type, exclude=None):
    if signal and signal.detected_objects and signal.energy > 0:
        for item in signal.detected_objects:
            if isinstance(item, entity_type) and item is not exclude:
                return item
    return False

@conditional()
def reproduce_possible(bot):
    if bot.energy > bot.child_investment:
        return True
    return False

@statement(seed_required=True)
def create_clone(bot):
    # Let's require the bot to have energy before it can do this
    if bot.energy > 0:
        # First the parent bot must pay an energy tax
        bot.world.drain_energy_from_entity(10, bot)
        child_behavior = bot.behavior.return_tree_copy()
        # Allow mutation
        if random_integers(1, 100) < 40:
            child_behavior.mutate_behavior()
        child = Bot(bot.x + random_integers(-3, 3), bot.y + random_integers(-3, 3),
                    generation_number=bot.generation_number+1, behavior_graph=child_behavior)
        # For now just start at the first node. Setting it to a random one could be interesting as well.
        child.behavior.set_entry_node(child.behavior.behavior_nodes[0])
        bot.world.transfer_energy_between_entities(bot.child_investment, donor=bot, recipient=child)
        bot.number_children += 1
        # print("%s spawned %s" % (str(bot), str(child)))
        bot.world.add_entity(child)

@statement()
def launch_signal(bot):
    # TODO: Make signal creation not require passing 0 and setting energy with a World method
    bot.signal = MobileSignal(bot.x, bot.y, bot.signal_direction, bot, color=(60, 60, 190))
    bot.world.transfer_energy_between_entities(10, donor=bot, recipient=bot.signal)

@conditional()
def signal_exists(bot):
    if bot.signal:
        return True
    return False

@statement()
def wait(bot):
    pass

@conditional()
def has_signal_found_plant(bot):
    plant = _check_detected_entity_type(bot.signal, Plant)
    if plant:
        bot.target_point = plant.x, plant.y
        return True
    return False

@statement()
def move_towards_target(bot):
    if bot.target_point:
        unit_vector = bot.world.get_unit_vector_to_point((bot.x, bot.y), (bot.target_point[0], bot.target_point[1]))
        bot.x += unit_vector[0] * bot.speed
        bot.y += unit_vector[1] * bot.speed

@conditional()
def target_nearby(bot):
    if bot.target_point:
        if math.sqrt(((bot.target_point[0] - bot.x)**2) + ((bot.target_point[1] - bot.y)**2)) <= 2:
            return True
    return False

@statement()
def eat_nearby_plants(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(120, 240, 130), max_age=2)
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

@statement()
def create_local_signal(bot):
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(40, 40, 180))
    bot.signal.diameter = 24
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)


@statement()
def create_long_range_signal(bot):
    bot.signal = MobileSignal(bot.x, bot.y, bot.signal_direction, bot, color=(150, 190, 240))
    bot.signal.diameter = 4
    bot.world.transfer_energy_between_entities(25, donor=bot, recipient=bot.signal)


@statement()
def set_random_target(bot):
    bot.target_point = bot.x + random_integers(-100, 100), bot.y + random_integers(-100, 100)


@statement(seed_eligible=False)
def eat_nearby_bots(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(240, 90, 90), max_age=2)
    bot.signal.diameter = 6
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)
    bot.signal.step()
    if bot.signal.detected_objects:
        for entity in bot.signal.detected_objects:
            if isinstance(entity, Bot) and entity is not bot:
                bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)


@conditional(seed_eligible=False)
def has_signal_found_bots(bot):
    other_bot = _check_detected_entity_type(bot.signal, Bot, exclude=bot)
    if other_bot:
        bot.target_point = other_bot.x, other_bot.y
        return True
    return False


@conditional(seed_eligible=False)
def has_signal_found_signal(bot):
    other_signal = _check_detected_entity_type(bot.signal, Signal, exclude=bot.signal)
    if other_signal:
        bot.target_point = other_signal.x, other_signal.y
        return True
    return False


@statement(seed_eligible=False)
def eat_nearby_signal(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, bot, color=(130, 130, 230), max_age=2)
    bot.signal.diameter = 6
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)
    bot.signal.step()
    entity = _check_detected_entity_type(bot.signal, Signal, exclude=bot.signal)
    if entity:
        bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)

@statement(seed_eligible=False)
def create_sniper_signal(bot):
    bot.signal = MobileSignal(bot.x, bot.y, bot.signal_direction, bot, color=(190, 220, 240))
    bot.signal.diameter = 2
    bot.world.transfer_energy_between_entities(50, donor=bot, recipient=bot.signal)

@conditional(seed_eligible=False)
def random_choice(bot):
    return random_integers(0, 1)

@conditional()
def very_low_energy(bot):
    if bot.energy < 100:
        return True
    return False

@statement(seed_eligible=False)
def set_target_to_signal_origin(bot):
    item = _check_detected_entity_type(bot.signal, Signal, exclude=bot.signal)
    if item:
        bot.target_point = item.x, item.y

@statement(seed_eligible=False)
def increment_message_type(bot):
    bot.message_signal_type += 1
    if bot.message_signal_type > 2:
        bot.message_signal_type = 0

def _check_message_type(bot, message_type):
    item = _check_detected_entity_type(bot.signal, Signal, exclude=bot.signal)
    return True if item and item.message_signal_type == message_type else False

@conditional(seed_eligible=False)
def detected_message_zero(bot):
    return _check_message_type(bot, 0)

@conditional(seed_eligible=False)
def detected_message_one(bot):
    return _check_message_type(bot, 1)

@conditional(seed_eligible=False)
def detected_message_two(bot):
    return _check_message_type(bot, 2)

@statement()
def set_random_signal_direction(bot):
    bot.signal_direction = ranf()*2*math.pi

@statement()
def move_towards_signal_direction(bot):
    if bot.signal_direction:
        unit_vector = math.cos(bot.signal_direction), math.sin(bot.signal_direction)
        bot.x += unit_vector[0] * bot.speed
        bot.y += unit_vector[1] * bot.speed

@statement()
def surround_push(bot):
    signal = StaticSignal(bot.x, bot.y, bot, color=(205, 205, 40), max_age=2)
    bot.world.transfer_energy_between_entities(80, donor=bot, recipient=signal)
    signal.diameter = 18
    bot.signal = signal
    bot.signal.step()
    if signal.detected_objects:
        for item in signal.detected_objects:
            if isinstance(item, Bot) and item is not bot:
                dx, dy = item.x - signal.x, item.y - signal.y
                radians = math.atan2(dy, dx)
                radius = signal.diameter/2
                item.x = signal.x + (radius * math.cos(radians))
                item.y = signal.y + (radius * math.sin(radians))
