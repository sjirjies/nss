import os
from matplotlib import pyplot as plt
from random import randint
import matplotlib.gridspec as gridspec
import csv
import time
import pygame
from scipy.spatial import cKDTree

from sim_entities import *
import behavior_functions

# TODO: Convert to an MVC model
#   - Get rid of graphical vs non-graphical mode
#   - Create a Model, which is the simulation
#   - Create a View that reads from World
#   - Create a Controller that uses the World API
# TODO: Have signals carry the location of their origination
# TODO: Have signals carry a 'message number' from 0-3
# TODO: Create a World Parameters class that can parse JSON parameters to initialize the world
# TODO: Create a Camera that can be panned and zoomed
# TODO: Create a right-pane that displays world information and trends
# TODO: Improve the APIs


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
        return True

    def _add_bot(self, bot):
        if self.bot_limit and len(self.bots) >= self.bot_limit:
            return False
        self.bots.append(bot)
        return True

    def _add_signal(self, signal):
        self.signals.append(signal)
        return True

    def add_entity(self, entity):
        # Note: add energy to entities before adding them, or they will be refused.
        if entity.energy < 0:
            return False
        if isinstance(entity, Signal):
            success = self._add_signal(entity)
        elif isinstance(entity, Plant):
            success = self._add_plant(entity)
        elif isinstance(entity, Bot):
            success = self._add_bot(entity)
        else:
            raise ValueError("%s is %s. Must be either a Signal, Plant, or Bot" % (entity, type(entity)))
        if success:
            entity.world = self
            entity.birthday = self.tick_number
            if self.boundary_sizes:
                entity.x = entity.x % self.boundary_sizes[0]
                entity.y = entity.y % self.boundary_sizes[1]
        return success

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
        if energy_to_give >= 0:
            if self.energy_pool is not None:
                if self.energy_pool < energy_to_give:
                    energy_to_give = self.energy_pool
                self.energy_pool -= energy_to_give
            entity.energy += energy_to_give
            return True
        return False

    def drain_energy_from_entity(self, energy_to_drain, entity):
        if energy_to_drain >= 0:
            if entity.energy <= energy_to_drain:
                energy_to_drain = entity.energy
                entity.dead = True
            entity.energy -= energy_to_drain
            if self.energy_pool is not None:
                self.energy_pool += energy_to_drain
            return True
        else:
            return False

    def transfer_energy_between_entities(self, energy_to_transfer, *, donor, recipient):
        if recipient.dead or donor.dead:
            return False
        if donor.energy <= energy_to_transfer:
            energy_to_transfer = donor.energy
            donor.dead = True
        donor.energy -= energy_to_transfer
        recipient.energy += energy_to_transfer
        return True

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

    def populate(self, number_bots, bot_energy, default_behavior=None, behavior_size=8):
        if self.energy_pool is not None:
            if bot_energy * number_bots < self.energy_pool:
                print("World has %d free energy, enough to seed with %d bots with %d energy each." %
                      (int(self.energy_pool), int(self.energy_pool//bot_energy), bot_energy))
            if self.energy_pool < bot_energy:
                print("Not enough free energy for even a single bot.")
                return False
        # Populate the world with bots
        for bot in range(0, number_bots):
            if not default_behavior:
                behavior = BehaviorGraph()
                behavior.generate_random_graph(behavior_size)
            else:
                behavior = default_behavior.return_tree_copy()
            if self.boundary_sizes:
                x = randint(0, self.boundary_sizes[0])
                y = randint(0, self.boundary_sizes[1])
            else:
                x = randint(0, 100)
                y = randint(0, 100)
            bot = Bot(x, y, behavior_graph=behavior)
            if self.energy_pool is not None and self.energy_pool < bot_energy:
                break
            self.add_entity(bot)
            self.give_energy_to_entity(bot_energy, bot)
        return True


def create_basic_intelligence():
    check_reproduce_node = ConditionalNode(behavior_functions.reproduce_possible)
    create_clone_node = StatementNode(behavior_functions.create_clone)
    launch_signal_node = StatementNode(behavior_functions.launch_signal)
    check_active_signal_node = ConditionalNode(behavior_functions.signal_exists)
    check_signal_found_food_node = ConditionalNode(behavior_functions.has_signal_found_food)
    wait_node = StatementNode(behavior_functions.wait)
    move_to_target_node = StatementNode(behavior_functions.move_towards_target)
    check_at_target_node = ConditionalNode(behavior_functions.target_nearby)
    eat_node = StatementNode(behavior_functions.eat_nearby_plants)

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


class SimulationData:
    def __init__(self, world):
        self.start_time = time.time()
        self.world = world
        self.plant_numbers = []
        self.bot_numbers = []
        self.signal_numbers = []
        # Create a dummy 'best bot' for now
        self.best_bot = Bot(0, 0, name='Dummy_Bot')
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
        self.save_bot_intelligence(best)

    def save_bot_intelligence(self, bot):
        has_network_x = True
        try:
            import networkx as nx
        except ImportError:
            print("Could not load Networkx module. Skipping intelligence graph creation.")
            has_network_x = False
        if has_network_x:
            # TODO: Make BehaviorGraph track the launch node and mark it in the graph output
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
            plt.title("%s: Born:%s, Age:%s, Peak Energy:%s, Children:%s" %
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


class ViewPort:
    def __init__(self, world, width, height):
        self.world = world
        self.surface_width = width
        self.surface_height = height
        self.surface = pygame.Surface((width, height))

    def render(self):
        self.surface.fill((0, 0, 0))
        pixels = pygame.surfarray.pixels3d(self.surface)
        for entity_list, color in [(self.world.plants, (40, 200, 40)), (self.world.bots, (200, 40, 200))]:
            for entity in entity_list:
                if 0 <= entity.x < self.surface_width and 0 <= entity.y < self.surface_height:
                    if isinstance(entity, Plant):
                        ratio = entity.energy/entity.max_energy
                        color = (int(40 * ratio), int(240 * ratio), int(40 * ratio))
                    pixels[entity.x][entity.y] = color
        del pixels
        self.surface.lock()
        for signal in self.world.signals:
            diameter = signal.diameter
            left = signal.x - (diameter/2)
            top = signal.y - (diameter/2)
            signal_color = signal.color if signal.color else (75, 75, 75)
            pygame.draw.ellipse(self.surface, signal_color, (left, top, diameter, diameter), 1)
        self.surface.unlock()


class Simulation:
    def __init__(self, world, plant_growth_ticks, initial_bots, initial_bot_energy, collect_data=True,
                 fps=20, scale=2, default_behavior=None):
        # Set an environment variable to center the pygame screen
        # TODO: Move display stuff into the View
        self.world = world
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        self.clock = pygame.time.Clock()
        if world.boundary_sizes:
            view_port_width, view_port_height = world.boundary_sizes
            # window_width += 60
        else:
            view_port_width, view_port_height = 300, 300
        self.view_port = ViewPort(self.world, view_port_width, view_port_height)
        self.window_width, self.window_height = scale * view_port_width, scale * view_port_height
        self.window = pygame.display.set_mode((self.window_width, self.window_height), pygame.DOUBLEBUF)
        pygame.display.set_caption('NSS')
        self.paused = False
        self.running = True
        self.tick = 0
        self.scale = scale
        self.fps = fps
        if collect_data:
            self.data_collector = SimulationData(self.world)
        else:
            self.data_collector = None
        self.seed_plants(plant_growth_ticks)
        # Populate the world with bots
        print("Adding bots...")
        self.world.populate(initial_bots, initial_bot_energy, default_behavior, behavior_size=8)
        # TODO: Account for paused time in the SimulationData results
        self.mainloop()

    def mainloop(self):
        while self.running:
            self.handle_user_input()
            # Update the world
            if not self.paused:
                self.world.step()
                # Collect Data if enabled
                self.collect_data()
                self.draw_graphics()
                self.tick += 1
            pygame.display.update()
            self.clock.tick(self.fps)
            # If we have no more entities then end the simulation
            if len(self.world.bots) == 0 or len(self.world.all_entities) == 0:
                print("Ending because all bots have died off.")
                self.running = False
        self.exit()

    def exit(self):
        print("World ran for %s ticks" % self.world.tick_number)
        pygame.quit()
        if self.data_collector:
            self.data_collector.save_metrics()

    def handle_user_input(self):
        for event in pygame.event.get():
            # Let the user quick the simulation
            if event.type == pygame.QUIT:
                self.running = 0
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = 0
            # Let the user pause the simulation
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.paused = False if self.paused else True

    def draw_graphics(self):
        self.view_port.render()
        # Draw the views to the window
        if self.scale > 1:
            pygame.transform.scale(self.view_port.surface, (self.window_width, self.window_height), self.window)
        else:
            self.window.blit(self.view_port.surface, (0, 0))

    def seed_plants(self, plant_growth_ticks):
        if self.world.boundary_sizes:
            x, y = self.world.half_boundaries[0], self.world.half_boundaries[1]
        else:
            x, y = 0, 0
        plant = Plant(x, y)
        self.world.add_entity(plant)
        self.world.give_energy_to_entity(5, plant)
        print("Running %s ticks with just plants..." % plant_growth_ticks)
        for i in range(plant_growth_ticks):
            self.world.step()
            self.collect_data()

    def collect_data(self):
        if self.data_collector:
            self.data_collector.poll_world_for_data()

if __name__ == '__main__':
    print("Starting Simulation...")
    earth = World(boundary_sizes=(250, 250), energy_pool=100000)
    start_behavior = create_basic_intelligence()
    Simulation(earth, 500, 100, 250, collect_data=True, fps=20, scale=2, default_behavior=start_behavior)