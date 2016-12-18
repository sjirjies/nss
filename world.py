import os
import csv
import time
import math
import numpy as np
from sim_entities import Bot, Plant, Signal
from intelligence import BehaviorGraph
from random import randint
from scipy.spatial import cKDTree
from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec
from intelligence import NodeRegister

graphviz_installed = False
networkx_installed = False
try:
    import graphviz as gv
    graphviz_installed = True
except:
    graphviz_installed = False
    print("Could not load graphviz moodule")
    try:
        import networkx as nx
        networkx_installed = True
    except:
        print("Also could not load networkx module")
        print("Intelligence graphing is disabled")


class World:
    def __init__(self, bot_limit=None, plant_limit=None, boundary_sizes=None, energy_pool=None):
        self.tick_number = 0
        self.start_time = time.time()
        self.time = time.time()
        self.bots = []
        self.plants = []
        self.signals = []
        self.bot_limit = bot_limit
        self.plant_limit = plant_limit
        self.boundary_sizes = boundary_sizes
        self.half_boundaries = None
        self.selected_bot = None
        if self.boundary_sizes:
            self.half_boundaries = self.boundary_sizes[0]/2, self.boundary_sizes[1]/2
        self.energy_pool = energy_pool
        self.initialized_energy = self.energy_pool
        self.kd_tree = None
        self.all_entities = []
        self.recently_dead_bots = []

    def step(self):
        self.time = time.time() - self.start_time
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
                        if entity is self.selected_bot:
                            self.selected_bot = None
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
            if bot_energy * number_bots > self.energy_pool:
                print("World has %d free energy, enough to seed with %d bots each with %d energy." %
                      (int(self.energy_pool), int(self.energy_pool//bot_energy), bot_energy))
            if self.energy_pool < bot_energy:
                print("Not enough free energy for even a single bot.")
                print("Deleting food until there is enough free energy.")
                while (number_bots * bot_energy) > self.energy_pool:
                    plant = self.plants.pop()
                    self.energy_pool += plant.energy
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
                x = randint(-50, 50)
                y = randint(-50, 50)
            bot = Bot(x, y, 1, behavior_graph=behavior)
            if self.energy_pool is not None and self.energy_pool < bot_energy:
                break
            self.add_entity(bot)
            self.give_energy_to_entity(bot_energy, bot)
        return True


class WorldWatcher:
    # TODO: Have info polling reduce data size through averaging when it becomes too large
    def __init__(self, world):
        # TODO: Get time from world
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
        self.bot_compare_function = WorldWatcher.default_bot_compare
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
            self.best_bot = self.bot_compare_function(self.best_bot, bot)

    @staticmethod
    def default_bot_compare(first_bot, second_bot):
        if first_bot.peak_energy > second_bot.peak_energy:
            return first_bot
        else:
            return second_bot

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
            self.best_bot = self.bot_compare_function(self.best_bot, bot)
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
        WorldWatcher.save_bot_intelligence(best, os.getcwd() + os.sep + 'metrics' + os.sep + 'intelligence_graph')

    @staticmethod
    def save_bot_intelligence(bot, file_path):
        if graphviz_installed:
            WorldWatcher._graph_intelligence_gv(bot, file_path)
        elif networkx_installed:
            WorldWatcher._graph_intelligence_nx(bot, file_path)
        else:
            print("Cannot save intelligence: no graph module found")

    @staticmethod
    def _graph_intelligence_nx(bot, file_path):
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
        plt.savefig(file_path + '.png', dpi=80, pad_inches=0.0, bbox_inches='tight')

    @staticmethod
    def _graph_intelligence_gv(bot, file_path):
        title = "Name: %s\nBorn: %s, Generation: %s, Age: %s\nPeak Energy: %s, Children: %s, Brain Size: %s" %\
                (str(bot), str(bot.birthday), str(bot.generation_number), str(bot.age),
                 str(bot.peak_energy), str(bot.number_children), str(len(bot.behavior.behavior_nodes)))
        graph = gv.Digraph(format='svg',  name=title, graph_attr={'label': title, 'ratio': 'auto', 'labelloc': 'b'})
        behavior_nodes = bot.behavior.behavior_nodes
        functions = [node.function for node in behavior_nodes]
        attributes = {'fontsize': '8'}
        statement_color = '#182BA6'
        conditional_color = '#A61835'
        statement_attributes = dict(attributes)
        statement_attributes['fillcolor'] = statement_color
        statement_attributes['color'] = statement_color
        conditional_attributes = dict(attributes)
        conditional_attributes['fillcolor'] = conditional_color
        conditional_attributes['color'] = conditional_color
        entry_attributes = dict(attributes)
        entry_attributes['style'] = 'filled'
        entry_attributes['fillcolor'] = '#DEDEDE'
        names = {}
        for index, node in enumerate(behavior_nodes):
            node_name = str(node.function.__name__).replace('_', '\n')
            if node.function in functions[:index]:
                count = functions.count(node.function)
                node_name += '_' + str(count)
            names[node] = node_name
            attr = statement_attributes if node.node_type == NodeRegister.statement else conditional_attributes
            if node is bot.behavior.entry_node:
                attr = entry_attributes
                attr['color'] = statement_color if node.node_type == NodeRegister.statement else conditional_color
            graph.node(node_name, _attributes=attr)
        for node in behavior_nodes:
            if node.node_type == NodeRegister.statement:
                graph.edge(names[node], names[node.next_node], _attributes=statement_attributes)
            else:
                graph.edge(names[node], names[node.true_node], 'T', _attributes=conditional_attributes)
                graph.edge(names[node], names[node.false_node], 'F', _attributes=conditional_attributes)
        graph.render(file_path)
        # Remove the temporary file created by graphviz
        os.remove(file_path)
