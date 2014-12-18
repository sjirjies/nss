import os
from matplotlib import pyplot as plt
import time
import pygame

from entities import *


class World:
    def __init__(self, bot_limit=None, plant_limit=None, boundary_sizes=None):
        self.bots = []
        self.plants = []
        self.signals = []
        self.bot_limit = bot_limit
        self.plant_limit = plant_limit
        self.boundary_sizes = boundary_sizes

    def step(self):
        # Update all plants then all bots
        for array in [self.plants, self.bots, self.signals]:
            for entity in list(array):
                entity.step()
                # Make sure the entity wraps around the boundaries
                if self.boundary_sizes:
                    entity.x = entity.x % self.boundary_sizes[0]
                    entity.y = entity.y % self.boundary_sizes[1]
                # Take care of dead entities
                if entity.dead:
                    if isinstance(entity, Bot):
                        print("%s has died" % str(entity))
                    array.remove(entity)

    def add_bot(self, bot):
        if self.bot_limit and len(self.bots) >= self.bot_limit:
            return False
        else:
            bot.world = self
            self.bots.append(bot)

    def add_plant(self, plant):
        if self.plant_limit and len(self.plants) >= self.plant_limit:
            return False
        plant.world = self
        self.plants.append(plant)


def no_graphics_run():

    def run(ticks):
        for tick in range(ticks):
            earth.step()
            # Keep track of some info for graphing
            plant_numbers.append(len(earth.plants))
            bot_numbers.append(len(earth.bots))

    run(500)

    run(1000)

    def graph_results():
        # Create some graphs to get a sense of what's going on
        graph = plt.figure()
        graph.subplots_adjust(wspace=0.4)
        graph.subplots_adjust(hspace=0.4)
        plant_dist = graph.add_subplot(2, 2, 1)
        plant_dist.scatter([plant.x for plant in earth.plants], [plant.y for plant in earth.plants], s=2, lw=0)
        plant_dist.set_xlabel('X')
        plant_dist.set_ylabel('Y')

        plant_nums = graph.add_subplot(2, 2, 2)
        plant_nums.set_xlabel('Time')
        plant_nums.set_ylabel('Number of Plants')
        plant_nums.plot(range(0, len(plant_numbers)), plant_numbers)

        bot_dist = graph.add_subplot(2, 2, 3)
        bot_dist.scatter([bot.x for bot in earth.bots], [bot.y for bot in earth.bots], s=2, lw=0)
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


class GraphicalSimulation:
    def __init__(self, world):
        pygame.init()
        screen_width, screen_height = 500, 500
        if world.boundary_sizes:
            screen_width, screen_height = world.boundary_sizes
        screen = pygame.display.set_mode((screen_width, screen_height))
        self.clock = pygame.time.Clock()
        running = 1
        tick = 0
        self.world = world
        # Run the simulation to get plants spread out
        earth.add_plant(Plant(screen_width/2, screen_height/2, 5))
        for i in range(1000):
            self.world.step()
        # Add a bot and display the simulation
        behavior = GraphicalSimulation.create_basic_intelligence()
        self.world.add_bot(Bot(screen_width/2, screen_height/2, 250, behavior))
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = 0
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = 0
            screen.fill((1, 2, 3))
            pygame.display.flip()
            # Do stuff
            # Update the world
            self.world.step()
            # Draw the plants and bots
            pixels = pygame.surfarray.pixels3d(screen)
            for entity_list, color in [(self.world.plants, (40, 200, 40)), (self.world.bots, (150, 40, 150))]:
                for entity in entity_list:
                    # Offset the origin to half the screen dimensions
                    x = entity.x
                    y = entity.y
                    if 0 <= x <= screen_width and 0 <= y <= screen_height:
                        pixels[x][y] = color
                    # pygame.draw.ellipse(screen, color, (x, y, 1, 1))
            for signal in self.world.signals:
                diameter = signal.diameter
                left = signal.x - (diameter/2)
                top = signal.y - (diameter/2)
                pygame.draw.ellipse(screen, (40, 50, 200), (left, top, diameter, diameter), 1)
            tick += 1
            pygame.display.update()
            self.clock.tick(10)
        pygame.quit()

    @staticmethod
    def create_basic_intelligence():
        check_reproduce_node = ConditionalNode(Bot.can_i_reproduce)
        create_clone_node = StatementNode(Bot.create_clone)
        launch_signal_node = StatementNode(Bot.launch_signal)
        check_active_signal_node = ConditionalNode(Bot.do_i_have_a_signal)
        check_signal_found_food_node = ConditionalNode(Bot.has_signal_found_food)
        wait_node = StatementNode(Bot.wait)
        move_to_target_node = StatementNode(Bot.move_towards_target)
        check_at_target_node = ConditionalNode(Bot.am_i_near_target)
        eat_node = StatementNode(Bot.eat_nearby_food)

        check_reproduce_node.assign_edges(create_clone_node, launch_signal_node)
        create_clone_node.assign_edge(check_reproduce_node)
        launch_signal_node.assign_edge(check_signal_found_food_node)
        check_signal_found_food_node.assign_edges(move_to_target_node, wait_node)
        wait_node.assign_edge(check_active_signal_node)
        check_active_signal_node.assign_edges(check_signal_found_food_node, launch_signal_node)
        move_to_target_node.assign_edge(check_at_target_node)
        check_at_target_node.assign_edges(eat_node, move_to_target_node)
        eat_node.assign_edge(check_reproduce_node)

        behavior = BehaviorTree()
        behavior.behavior_nodes = [launch_signal_node, check_reproduce_node, create_clone_node,
                                   check_signal_found_food_node, wait_node,move_to_target_node, check_at_target_node,
                                   eat_node, check_active_signal_node]
        behavior.current_behavior_node = launch_signal_node
        return behavior

if __name__ == '__main__':
    print("Starting Simulation...")
    start_time = time.time()
    earth = World(plant_limit=600, boundary_sizes=(500, 500))
    plant_numbers = []
    bot_numbers = []
    GraphicalSimulation(earth)
    print("Elapsed seconds:", time.time() - start_time)
