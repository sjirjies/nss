import random
import os
from matplotlib import pyplot as plt
import numpy as np
import time

from entities import *
from intelligence import *


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
    Earth = World(plant_limit=1000)
    Earth.add_plant(Plant(0, 0, 5))
    plant_numbers = []
    bot_numbers = []

    def run(ticks):
        for tick in range(ticks):
            Earth.step()
            # Keep track of some info for graphing
            plant_numbers.append(len(Earth.plants))
            bot_numbers.append(len(Earth.bots))

    run(500)

    # Create basic nodes
    basic_behavior = BehaviorTree()
    check_if_can_clone_node = BehaviorNode(Bot.can_i_reproduce)
    create_clone_node = BehaviorNode(Bot.create_clone)
    target_food_node = BehaviorNode(Bot.target_food)
    move_to_target_node = BehaviorNode(Bot.move_towards_target)
    check_near_target_node = BehaviorNode(Bot.am_i_near_target)
    eat_node = BehaviorNode(Bot.eat_nearby_food)

    # Wire the nodes together
    check_if_can_clone_node.true_node = create_clone_node
    check_if_can_clone_node.false_node = target_food_node
    create_clone_node.next_node = check_if_can_clone_node
    target_food_node.next_node = move_to_target_node
    move_to_target_node.next_node = check_near_target_node
    check_near_target_node.false_node = move_to_target_node
    check_near_target_node.true_node = eat_node
    eat_node.next_node = check_if_can_clone_node

    basic_behavior.behavior_nodes = [check_if_can_clone_node, create_clone_node, target_food_node,
                                     move_to_target_node, check_near_target_node, eat_node]

    basic_behavior.current_behavior_node = check_if_can_clone_node
    Earth.add_bot(Bot(0, 0, 200, behavior_tree=basic_behavior.return_tree_copy()))
    run(1000)

    def graph_results():
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

    graph_results()
    print("Elapsed seconds:", time.time() - start_time)