from numpy.random import random_integers
from intelligence import statement, conditional
from sim_entities import Plant, Bot, MobileSignal, StaticSignal, Signal

from numpy.random import random_integers, ranf
import math


@statement
def create_local_signal(bot):
    bot.signal = StaticSignal(bot.x, bot.y, 2, bot)
    bot.signal.diameter = 16
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)


@statement
def create_long_range_signal(bot):
    # TODO: Allow bots to store a direction for their signal propagation instead of using a random one
    bot.signal = MobileSignal(bot.x, bot.y, ranf()*2*math.pi, 0, bot)
    bot.signal.diameter = 2
    bot.world.transfer_energy_between_entities(25, donor=bot, recipient=bot.signal)


@statement
def set_random_target(bot):
    bot.target_point = bot.x + random_integers(-100, 100), bot.y + random_integers(-100, 100)


@statement
def kill_and_eat_nearby_bots(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, 2, bot)
    bot.signal.diameter = 4
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)
    bot.signal.step()
    if bot.signal.detected_objects:
        for entity in bot.signal.detected_objects:
            if isinstance(entity, Bot) and entity is not bot:
                bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)


@conditional
def has_signal_detected_bots(bot):
    if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
        for item in bot.signal.detected_objects:
            if isinstance(item, Bot):
                # print("FOUND FOOD %s at %d, %d" % (item, item.x, item.y))
                bot.target_point = item.x, item.y
                return True
    return False


@conditional
def has_signal_detected_other_signal(bot):
    if bot.signal and bot.signal.detected_objects and bot.signal.energy > 0:
        for item in bot.signal.detected_objects:
            if isinstance(item, Bot) and item is not bot.signal:
                # print("FOUND FOOD %s at %d, %d" % (item, item.x, item.y))
                bot.target_point = item.x, item.y
                return True
    return False


@statement
def consume_nearby_signal(bot):
    if bot.signal:
        bot.signal.dead = True
    bot.signal = StaticSignal(bot.x, bot.y, 2, bot)
    bot.signal.diameter = 4
    bot.world.transfer_energy_between_entities(2, donor=bot, recipient=bot.signal)
    bot.signal.step()
    if bot.signal.detected_objects:
        for entity in bot.signal.detected_objects:
            if isinstance(entity, Signal) and entity is not bot.signal:
                bot.world.transfer_energy_between_entities(entity.energy, donor=entity, recipient=bot)