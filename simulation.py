import os
from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec
import time
import pygame
from scipy.spatial import cKDTree

from sim_entities import *


class World:
    def __init__(self, bot_limit=None, plant_limit=None, boundary_sizes=None, energy_pool=None):
        self.tick_number = 0
        self.bots = []
        self.plants = []
        self.signals = []
        self.bot_limit = bot_limit
        self.plant_limit = plant_limit
        self.boundary_sizes = boundary_sizes
        self.energy_pool = energy_pool
        self.kd_tree = None
        self.all_entities = []

    def step(self):
        self.tick_number += 1
        # Update the list of all entities
        self.aggregate_entities()
        # Build a new kd tree to account for movement from the last tick
        self.build_kd_tree()
        # Update all plants then all bots
        for array in [self.plants, self.bots, self.signals]:
            for entity in list(array):
                # Take care of dead entities
                if entity.dead:
                    # if isinstance(entity, Bot):
                    #    print("%s has died" % str(entity))
                    # Transfer any remaining energy back into the world
                    if self.energy_pool is not None and entity.energy > 0:
                        self.energy_pool += entity.energy
                    array.remove(entity)
                else:
                    # Make sure the entity wraps around the boundaries
                    if self.boundary_sizes:
                        entity.x = entity.x % self.boundary_sizes[0]
                        entity.y = entity.y % self.boundary_sizes[1]
                    entity.step()

    def _add_plant(self, plant):
        if self.plant_limit and len(self.plants) >= self.plant_limit:
            return False
        self.plants.append(plant)

    def _add_bot(self, bot):
        if self.bot_limit and len(self.bots) >= self.bot_limit:
            return False
        self.bots.append(bot)

    def _add_signal(self, signal):
        self.signals.append(signal)

    def add_entity(self, entity):
        # Note: add energy to entities before adding them, or they will be refused.
        if entity.energy == 0:
            return False
        if isinstance(entity, Signal):
            self._add_signal(entity)
        elif isinstance(entity, Plant):
            self._add_plant(entity)
        elif isinstance(entity, Bot):
            self._add_bot(entity)
        else:
            raise ValueError("%s is %s. Must be either a Signal, Plant, or Bot" % (entity, type(entity)))
        entity.world = self
        entity.birthday = self.tick_number

    def aggregate_entities(self):
        self.all_entities = []
        for entity_list in (self.plants, self.bots, self.signals):
            self.all_entities.extend(entity_list)

    def build_kd_tree(self):
        if len(self.all_entities) > 0:
            x_array = [p.x for p in self.all_entities]
            y_array = [p.y for p in self.all_entities]
            number_entities = len(self.all_entities)
            x_array = np.array(x_array)
            y_array = np.array(y_array)
            x_array = np.reshape(x_array, (number_entities, 1))
            y_array = np.reshape(y_array, (number_entities, 1))
            point_locations = np.hstack((x_array, y_array))
            self.kd_tree = cKDTree(point_locations, leafsize=15)

    def give_energy_to_entity(self, energy_to_give, entity):
        if self.energy_pool is not None:
            if self.energy_pool < energy_to_give:
                energy_to_give = self.energy_pool
            self.energy_pool -= energy_to_give
        entity.energy += energy_to_give

    def drain_energy_from_entity(self, energy_to_drain, entity):
        if entity.energy <= energy_to_drain:
            energy_to_drain = entity.energy
            entity.dead = True
        entity.energy -= energy_to_drain
        if self.energy_pool is not None:
            self.energy_pool += energy_to_drain

    def transfer_energy_between_entities(self, energy_to_transfer, *, donor, recipient):
        if donor.energy <= energy_to_transfer:
            energy_to_transfer = donor.energy
            donor.dead = True
        donor.energy -= energy_to_transfer
        recipient.energy += energy_to_transfer


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


def no_graphics_run(world, plant_growth_ticks, additional_ticks, collect_data=True):
    if collect_data:
        sim_data = SimulationData(world)
    else:
        sim_data = None

    def run(ticks, with_bots):
        for tick in range(ticks):
            world.step()
            # Keep track of some info for graphing
            if sim_data:
                sim_data.poll_world_for_data()
            if with_bots and len(world.bots) == 0:
                print("Stopping %s ticks in since no more bots." % tick)
                return
            if tick % 100 == 0:
                print(" Finished Tick %d / %d" % (tick, ticks))

    center = world.boundary_sizes[0]/2, world.boundary_sizes[1]/2
    world.add_entity(Plant(center[0], center[1], 50))
    print("Running %s ticks with just plants..." % plant_growth_ticks)
    run(plant_growth_ticks, with_bots=False)
    behavior = create_basic_intelligence()
    world.add_entity(Bot(center[0], center[1], 300, behavior))
    print("Running %s ticks with bots added..." % additional_ticks)
    run(additional_ticks, with_bots=True)
    if sim_data:
        sim_data.graph_results()


class SimulationData:
    def __init__(self, world):
        self.world = world
        self.plant_numbers = []
        self.bot_numbers = []
        self.signal_numbers = []

    def poll_world_for_data(self):
        for data_list, world_list in ((self.plant_numbers, self.world.plants), (self.bot_numbers, self.world.bots),
                                      (self.signal_numbers, self.world.signals)):
            data_list.append(len(world_list))

    def graph_results(self):
        print("Creating Graph...")
        # Create some graphs to get a sense of what's going on
        grid = gridspec.GridSpec(2, 2)
        sub_graph_title_size = 8
        axes_text_size = 7
        legend_font_size = 7
        axes_tick_font_size = 6

        graph = plt.figure()
        graph.subplots_adjust(wspace=0.15)
        graph.subplots_adjust(hspace=0.15)

        entity_dist = graph.add_subplot(grid[0, 0])
        entity_dist.scatter([plant.x for plant in self.world.plants], [plant.y for plant in self.world.plants],
                            s=2, lw=0, label='Plants', c='g')
        entity_dist.scatter([bot.x for bot in self.world.bots], [bot.y for bot in self.world.bots],
                            s=3, lw=0, label='Bots', c='m')
        entity_dist.legend(loc='upper left', labelspacing=0, borderpad=0, fontsize=legend_font_size)
        x_limits = 0, self.world.boundary_sizes[0]
        y_limits = 0, self.world.boundary_sizes[1]
        if self.world.boundary_sizes:
            # Since the world has no bounds, find the spatial span of the entities
            x_points = [point.x for point in self.world.all_entities]
            y_points = [point.y for point in self.world.all_entities]
            x_limits = min(x_points), max(x_points)
            y_limits = min(x_points), max(y_points)
        entity_dist.set_xlim(x_limits)
        entity_dist.set_ylim(y_limits)
        entity_dist.set_xlabel('X', size=axes_text_size)
        entity_dist.set_ylabel('Y', size=axes_text_size)

        entity_nums = graph.add_subplot(grid[1, :])
        entity_nums.set_xlabel('Tick', size=axes_text_size)
        entity_nums.set_ylabel('Number of Plants', size=axes_text_size)
        for entity_list, name, color in ((self.plant_numbers, 'Plants', 'g'), (self.bot_numbers, 'Bots', 'm'),
                                         (self.signal_numbers, 'Signals', 'b')):
            entity_nums.plot(range(0, len(entity_list)), entity_list, label=name, c=color)
        entity_nums.legend(loc='upper left', labelspacing=0, borderpad=0, fontsize=legend_font_size)
        entity_nums.set_xlim((0, self.world.tick_number))

        unused_graph = graph.add_subplot(grid[0, 1])
        unused_graph.set_xlabel('X', size=axes_text_size)
        unused_graph.set_ylabel('Y', size=axes_text_size)

        # Make all subplot axes tick labels smaller and give them a title
        for subplot, title in [(entity_dist, 'Entity Distribution'), (entity_nums, 'Entity Numbers'),
                               (unused_graph, 'Not Yet Used...')]:
            subplot.tick_params(labelsize=axes_tick_font_size)
            subplot.set_title(title, size=sub_graph_title_size)
        print("Saving Graph...")
        graph.savefig(os.getcwd() + os.sep + 'graphs' + os.sep + 'simulation.png', dpi=115, bbox_inches='tight')


class GraphicalSimulation:
    def __init__(self, world, plant_ticks, collect_data=True):
        # Set an environment variable to center the pygame screen
        os.environ['SDL_VIDEO_CENTERED'] = '1'
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
        self.world.add_entity(Plant(screen_width/2, screen_height/2, 5))
        if collect_data:
            sim_data = SimulationData(self.world)
        else:
            sim_data = None
        for i in range(plant_ticks):
            self.world.step()
            if sim_data:
                sim_data.poll_world_for_data()
        # Add a bot and display the simulation
        behavior = create_basic_intelligence()
        self.world.add_entity(Bot(screen_width/2, screen_height/2, 250, behavior))
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = 0
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = 0
            screen.fill((0, 0, 0))
            pygame.display.flip()
            # Update the world
            self.world.step()
            # Collect Data if enabled
            if sim_data:
                sim_data.poll_world_for_data()
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
                signal_color = (40, 50, 200)
                if isinstance(signal, StaticSignal):
                    signal_color = (100, 130, 250)
                pygame.draw.ellipse(screen, signal_color, (left, top, diameter, diameter), 1)
            tick += 1
            pygame.display.update()
            self.clock.tick(15)
            # If we have no more entities then end the simulation
            if len(self.world.bots) == 0 or len(self.world.all_entities) == 0:
                running = False
        if sim_data:
            sim_data.graph_results()
        pygame.quit()


def run_simulation(world, plant_growth_ticks, additional_ticks, graphics=False, collect_data=True):
    if graphics:
        GraphicalSimulation(world, plant_growth_ticks, collect_data=collect_data)
    else:
        no_graphics_run(world, plant_growth_ticks, additional_ticks, collect_data=collect_data)

if __name__ == '__main__':
    print("Starting Simulation...")
    start_time = time.time()
    earth = World(plant_limit=500, boundary_sizes=(200, 200))
    run_simulation(earth, 500, 5000, graphics=False)
    print("Elapsed seconds:", time.time() - start_time)
