import os
from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec
import csv
import time
import pygame
from scipy.spatial import cKDTree
import networkx as nx

from sim_entities import *
import extra_nodes


class World:
    def __init__(self, bot_limit=None, plant_limit=None, boundary_sizes=None, energy_pool=None):
        self.tick_number = 0
        self.bots = []
        self.plants = []
        self.signals = []
        self.bot_limit = bot_limit
        self.plant_limit = plant_limit
        self.boundary_sizes = boundary_sizes
        self.half_boundaries = None
        if self.boundary_sizes:
            self.half_boundaries = self.boundary_sizes[0]/2, self.boundary_sizes[1]/2
        self.energy_pool = energy_pool
        self.initialized_energy = self.energy_pool
        self.kd_tree = None
        self.all_entities = []
        self.recently_dead_bots = []

    def step(self):
        self.tick_number += 1
        self.recently_dead_bots = []
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
                    if isinstance(entity, Bot):
                        self.recently_dead_bots.append(entity)
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

    def get_unit_vector_to_point(self, start_point, target_point):
        x_diff, y_diff = target_point[0] - start_point[0], target_point[1] - start_point[1]
        if self.boundary_sizes:
            if x_diff > self.half_boundaries[0]:
                x_diff = (x_diff - self.boundary_sizes[0])
            elif x_diff < -self.half_boundaries[0]:
                x_diff = (x_diff + self.boundary_sizes[0])
            if y_diff > self.half_boundaries[1]:
                y_diff = (y_diff - self.boundary_sizes[1])
            elif y_diff < -self.half_boundaries[1]:
                y_diff = (y_diff + self.boundary_sizes[1])
        distance = math.sqrt((x_diff**2) + (y_diff**2))
        if distance > 0:
            x_diff /= distance
            y_diff /= distance
        return x_diff, y_diff


def create_basic_intelligence():
    check_reproduce_node = ConditionalNode(Bot.reproduce_possible)
    create_clone_node = StatementNode(Bot.create_clone)
    launch_signal_node = StatementNode(Bot.launch_signal)
    check_active_signal_node = ConditionalNode(Bot.signal_exists)
    check_signal_found_food_node = ConditionalNode(Bot.has_signal_found_food)
    wait_node = StatementNode(Bot.wait)
    move_to_target_node = StatementNode(Bot.move_towards_target)
    check_at_target_node = ConditionalNode(Bot.target_nearby)
    eat_node = StatementNode(Bot.eat_nearby_plants)

    check_reproduce_node.assign_edges(create_clone_node, launch_signal_node)
    create_clone_node.assign_edge(check_reproduce_node)
    launch_signal_node.assign_edge(check_signal_found_food_node)
    check_signal_found_food_node.assign_edges(move_to_target_node, wait_node)
    wait_node.assign_edge(check_active_signal_node)
    check_active_signal_node.assign_edges(check_signal_found_food_node, launch_signal_node)
    move_to_target_node.assign_edge(check_at_target_node)
    check_at_target_node.assign_edges(eat_node, move_to_target_node)
    eat_node.assign_edge(check_reproduce_node)

    behavior = BehaviorGraph()
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
        sim_data.save_metrics()


class SimulationData:
    def __init__(self, world):
        self.start_time = time.time()
        self.world = world
        self.plant_numbers = []
        self.bot_numbers = []
        self.signal_numbers = []
        # Create a dummy 'best bot' for now
        self.best_bot = Bot(0, 0, 0, name='Dummy_Bot')
        self.best_bot.birthday = 0
        self.directory = os.getcwd() + os.sep + 'metrics'
        self.hall_champions_file_path = self.directory + os.sep + 'hall_of_champions.csv'
        self.champions_intel_file_path = self.directory + os.sep + 'champions_intelligence.txt'
        # Create the metrics directory if it does not exist.
        if not os.path.exists(self.directory):
            print("Making metrics directory...")
            os.makedirs(self.directory)
        # Create the champions csv if it does not exist and write the header to it
        self.fieldnames = ('name', 'birthday', 'age', 'end_energy', 'peak_energy', 'children', 'world_ticks',
                           'world_width', 'world_height', 'bot_limit', 'plant_limit', 'energy_pool', 'seconds_run',
                           'YYYY-MM-DD', 'day_time')
        if not os.path.isfile(self.hall_champions_file_path):
            print("Creating Hall of Champions record...")
            with open(self.directory + os.sep + 'hall_of_champions.csv', 'a+') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
                writer.writeheader()

    def poll_world_for_data(self):
        for data_list, world_list in ((self.plant_numbers, self.world.plants), (self.bot_numbers, self.world.bots),
                                      (self.signal_numbers, self.world.signals)):
            data_list.append(len(world_list))
        for bot in self.world.recently_dead_bots:
            # Compare the recently deceased bot to the current best and return the better
            self.keep_better_bot(self.best_bot, bot)

    def keep_better_bot(self, first_bot, second_bot):
        if first_bot.peak_energy > second_bot.peak_energy:
            self.best_bot = first_bot
        else:
            self.best_bot = second_bot

    def save_metrics(self):
        self.graph_population_data()
        self.save_champion_bot_data()
        print("Total elapsed seconds:", round(time.time() - self.start_time, 2), "seconds.")

    def graph_population_data(self):
        print("Saving Graph...")
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
        if self.world.boundary_sizes:
            x_limits = 0, self.world.boundary_sizes[0]
            y_limits = 0, self.world.boundary_sizes[1]
        else:
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
            entity_nums.plot(range(0, len(entity_list)), entity_list, label=name, c=color, linewidth=0.35)
        entity_nums.legend(loc='upper left', labelspacing=0, borderpad=0, fontsize=legend_font_size)
        entity_nums.set_xlim((0, self.world.tick_number))

        unused_graph = graph.add_subplot(grid[0, 1])
        unused_graph.set_xlabel('X', size=axes_text_size)
        unused_graph.set_ylabel('Y', size=axes_text_size)

        # Make all subplot axes tick labels smaller and give them a title
        for subplot, title in [(entity_dist, 'Entity Distribution'), (entity_nums, 'Entity Numbers'),
                               (unused_graph, 'Not Used Yet...')]:
            subplot.tick_params(labelsize=axes_tick_font_size)
            subplot.set_title(title, size=sub_graph_title_size)
        graph.savefig(self.directory + os.sep + 'simulation.png', dpi=115, bbox_inches='tight')

    def save_champion_bot_data(self):
        # First find if any of the still alive bots are better
        for bot in self.world.bots:
            self.keep_better_bot(self.best_bot, bot)
        best = self.best_bot
        today = time.strftime('%Y-%m-%d')
        hour_min = time.strftime('%H:%M')
        print("Updating Hall of Champions...")
        with open(self.directory + os.sep + 'hall_of_champions.csv', 'a+') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
            # Collect the values for the new row and write it to the CSV
            if self.world.boundary_sizes:
                world_width, world_height = self.world.boundary_sizes
            else:
                world_width, world_height = '-1', '-1'
            bot_limit = '-1' if self.world.bot_limit is None else self.world.bot_limit
            plant_limit = '-1' if self.world.plant_limit is None else self.world.plant_limit
            energy_pool = '-1' if self.world.initialized_energy is None else self.world.initialized_energy
            values = (best.name, best.birthday, best.age, best.energy, best.peak_energy, best.number_children,
                      self.world.tick_number, world_width, world_height, bot_limit, plant_limit, energy_pool,
                      round(time.time() - self.start_time, 1), today, hour_min)
            writer.writerow(dict(zip(self.fieldnames, values)))
        # TODO: Replace the text output with a visual graph using something like NetworkX http://networkx.github.io/
        print("Updating Champions Intelligence Text...")
        self.save_bot_intelligence(best)

    def save_bot_intelligence(self, bot):
        print("Saving Champion Intelligence Graph...")
        behavior_nodes = bot.behavior.behavior_nodes
        network = nx.DiGraph()
        network.add_nodes_from(behavior_nodes)
        # Add the behavior nodes to the network and link them together
        for node in behavior_nodes:
            if node.node_type == NodeRegister.statement:
                network.add_edge(node, node.next_node, label='')
            elif node.node_type == NodeRegister.conditional:
                network.add_edge(node, node.true_node, label='1')
                network.add_edge(node, node.false_node, label='0')
        # Draw the network
        layout = nx.shell_layout(network, scale=3)
        plt.figure(figsize=(10, 10))
        plt.axis('equal')
        plt.title("%s: Born:%s, Max Age:%s, Peak Energy:%s, Total Children:%s" %
                  (str(bot), str(bot.birthday), str(bot.age), str(bot.peak_energy), str(bot.number_children)))
        nx.draw_networkx_edges(network, layout, width=0.5, alpha=0.75, edge_color='black', arrows=True)
        statement_color = '#D7E7F7'
        conditional_color = '#F7D7DA'
        colors = [statement_color if node.node_type == NodeRegister.statement else conditional_color
                  for node in network.nodes()]
        nx.draw_networkx_nodes(network, layout, node_size=1800, node_color=colors, alpha=1)
        # Reformat node names to make them easier to read
        names = [(node, str(node.function.__name__).replace('_', '\n')) for node in behavior_nodes]
        labels = {key: value for (key, value) in names}
        nx.draw_networkx_labels(network, layout, labels, font_size=10, font_family='sans-serif')
        edge_names = nx.get_edge_attributes(network, 'label')
        nx.draw_networkx_edge_labels(network, layout, edge_labels=edge_names, label_pos=0.7)
        plt.axis('off')
        plt.savefig(self.directory + os.sep + 'intelligence_graph.png', dpi=80, pad_inches=0.0, bbox_inches='tight')


class GraphicalSimulation:
    def __init__(self, world, plant_ticks, collect_data=True, fps=20, scale=2):
        # Set an environment variable to center the pygame screen
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        self.clock = pygame.time.Clock()
        self.world = world
        if world.boundary_sizes:
            window_width, window_height = world.boundary_sizes
        else:
            window_width, window_height = 250, 250
        screen = pygame.Surface((window_width, window_height))
        screen_width, screen_height = screen.get_width(), screen.get_height()
        window_width, window_height = scale * window_width, scale * window_height
        window = pygame.display.set_mode((window_width, window_height), pygame.DOUBLEBUF)
        pygame.display.set_caption('NSS')
        running = 1
        tick = 0
        # Run the simulation to get plants spread out
        if self.world.boundary_sizes:
            self.world.add_entity(Plant(self.world.half_boundaries[0], self.world.half_boundaries[1], 5))
        else:
            self.world.add_entity(Plant(screen_width//2, screen_height//2, 5))
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
        if self.world.boundary_sizes:
            self.world.add_entity(Bot(self.world.half_boundaries[0], self.world.half_boundaries[1], 250, behavior))
        else:
            self.world.add_entity(Bot(screen_width//2, screen_height//2, 250, behavior))
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = 0
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = 0
            screen.fill((0, 0, 0))
            # Update the world
            self.world.step()
            # Collect Data if enabled
            if sim_data:
                sim_data.poll_world_for_data()
            # Draw the plants and bots
            pixels = pygame.surfarray.pixels3d(screen)
            for entity_list, color in [(self.world.plants, (40, 200, 40)), (self.world.bots, (150, 40, 150))]:
                for entity in entity_list:
                    if 0 <= entity.x < screen_width and 0 <= entity.y < screen_height:
                        pixels[entity.x][entity.y] = color
                    # pygame.draw.ellipse(screen, color, (x, y, 1, 1))
            del pixels
            screen.lock()
            for signal in self.world.signals:
                diameter = signal.diameter
                left = signal.x - (diameter/2)
                top = signal.y - (diameter/2)
                signal_color = (40, 50, 200)
                if isinstance(signal, StaticSignal):
                    signal_color = (100, 130, 250)
                pygame.draw.ellipse(screen, signal_color, (left, top, diameter, diameter), 1)
            screen.unlock()
            if scale > 1:
                pygame.transform.scale(screen, (window_width, window_height), window)
            else:
                window.blit(screen, (0, 0))
            tick += 1
            pygame.display.update()
            self.clock.tick(fps)
            # If we have no more entities then end the simulation
            if len(self.world.bots) == 0 or len(self.world.all_entities) == 0:
                running = False
        print("World ran for %s ticks" % self.world.tick_number)
        if sim_data:
            sim_data.save_metrics()
        pygame.quit()


def run_simulation(world, plant_growth_ticks, additional_ticks, graphics=False, collect_data=True, fps=20, scale=2):
    if graphics:
        GraphicalSimulation(world, plant_growth_ticks, collect_data=collect_data, fps=fps, scale=scale)
    else:
        no_graphics_run(world, plant_growth_ticks, additional_ticks, collect_data=collect_data)

if __name__ == '__main__':
    print("Starting Simulation...")
    earth = World(boundary_sizes=(250, 250), energy_pool=100000)
    run_simulation(earth, 500, 5000, graphics=True, fps=60, scale=1)