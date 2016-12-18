import time

from world import World, WorldWatcher
from sim_entities import *
from gui import *
import behavior_functions


# TODO: Create a World Parameters class that can parse JSON parameters to initialize the world
# TODO: Improve the APIs


def create_basic_brain():
    check_reproduce_node = ConditionalNode(behavior_functions.reproduce_possible)
    create_clone_node = StatementNode(behavior_functions.create_clone)
    launch_signal_node = StatementNode(behavior_functions.launch_signal)
    check_active_signal_node = ConditionalNode(behavior_functions.signal_exists)
    randomize_signal_direction = StatementNode(behavior_functions.set_random_signal_direction)
    check_signal_found_food_node = ConditionalNode(behavior_functions.has_signal_found_plant)
    wait_node = StatementNode(behavior_functions.wait)
    move_to_target_node = StatementNode(behavior_functions.move_towards_target)
    check_at_target_node = ConditionalNode(behavior_functions.target_nearby)
    eat_node = StatementNode(behavior_functions.eat_nearby_plants)

    check_reproduce_node.assign_edges(create_clone_node, check_active_signal_node)
    create_clone_node.assign_edge(check_reproduce_node)
    launch_signal_node.assign_edge(check_signal_found_food_node)
    check_signal_found_food_node.assign_edges(move_to_target_node, wait_node)
    wait_node.assign_edge(check_active_signal_node)
    check_active_signal_node.assign_edges(check_signal_found_food_node, randomize_signal_direction)
    randomize_signal_direction.assign_edge(launch_signal_node)
    move_to_target_node.assign_edge(check_at_target_node)
    check_at_target_node.assign_edges(eat_node, move_to_target_node)
    eat_node.assign_edge(check_reproduce_node)

    behavior = BehaviorGraph()
    behavior.behavior_nodes = [launch_signal_node, check_reproduce_node, create_clone_node,
                               check_signal_found_food_node, wait_node, move_to_target_node, check_at_target_node,
                               eat_node, check_active_signal_node, randomize_signal_direction]
    behavior.set_entry_node(launch_signal_node)
    return behavior


def create_very_simple_brain():
    check_reproduce_node = ConditionalNode(behavior_functions.reproduce_possible)
    create_clone_node = StatementNode(behavior_functions.create_clone)
    eat_node = StatementNode(behavior_functions.eat_nearby_plants)
    target_node = StatementNode(behavior_functions.set_random_target)
    move_target_node = StatementNode(behavior_functions.move_towards_target)

    target_node.assign_edge(move_target_node)
    move_target_node.assign_edge(eat_node)
    eat_node.assign_edge(check_reproduce_node)
    check_reproduce_node.assign_edges(create_clone_node, target_node)
    create_clone_node.assign_edge(target_node)
    behavior = BehaviorGraph()
    behavior.behavior_nodes = [check_reproduce_node, create_clone_node, eat_node, target_node, move_target_node]
    behavior.set_entry_node(target_node)
    return behavior


class Simulation:
    def __init__(self, world, plant_growth_ticks, initial_bots, initial_bot_energy,
                 fps=20, text_scale=2, graph_height=100, default_behavior=None,
                 default_brain_size=10):
        # Set an environment variable to center the pygame screen
        # TODO: Move display stuff into the View
        self.world = world
        self.data_collector = WorldWatcher(self.world)
        # os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        self.clock = pygame.time.Clock()
        # Set up the different views
        panel_text_color = (220, 220, 220)
        panel_bg_color = (10, 10, 10)
        text_panel_width = 90 * text_scale
        if world.boundary_sizes:
            view_port_width, view_port_height = world.boundary_sizes
        else:
            view_port_width, view_port_height = 500, 500
        self.view_port = ViewPort(self.world, view_port_width, view_port_height)
        self.info_panel = InfoPanel(self.world, self.clock, text_panel_width,
                                    view_port_height, text_scale, panel_text_color, panel_bg_color)
        self.bot_panel = BotPanel(self.world, text_panel_width,
                                  view_port_height, text_scale, panel_text_color, panel_bg_color)
        graph_panel_width = (text_panel_width * 2) + self.view_port.width
        self.graph_panel = GraphPanel(self.data_collector, graph_panel_width, graph_height, 1,
                                      panel_text_color, panel_bg_color)

        self.info_panel_position = ((0, 0), (self.info_panel.width, self.info_panel.height))
        self.view_port_position = ((self.info_panel.width, 0),
                                   (self.view_port.width, self.view_port.height))
        self.bot_panel_position = ((self.view_port_position[0][0] + self.view_port_position[1][0], 0),
                                   (self.bot_panel.width, self.info_panel.height))
        main_surface_width = view_port_width + self.info_panel.width + self.bot_panel.width
        main_surface_height = max(self.info_panel.height, 250 * text_scale) + graph_height
        self.graph_panel_position = ((0, self.info_panel.height), (graph_panel_width, self.info_panel.height))
        self.main_surface = pygame.Surface((main_surface_width, main_surface_height))
        self.window_width, self.window_height = main_surface_width, main_surface_height
        # Create the simulation window
        pygame.display.set_caption('NSS')
        pygame.display.set_icon(pygame.image.load(os.getcwd() + os.sep + 'nss_icon.png'))
        self.window = pygame.display.set_mode((self.window_width, self.window_height),
                                              pygame.DOUBLEBUF | pygame.RESIZABLE)
        self.paused = False
        self.running = True
        self.tick = 0
        self.text_scale = text_scale
        self.fps = fps
        self.seed_plants(plant_growth_ticks)
        # Populate the world with bots
        print("Adding bots...")
        self.world.populate(initial_bots, initial_bot_energy, default_behavior, behavior_size=default_brain_size)
        # TODO: Account for paused time in the WorldWatcher results
        # Create a mouse handler and enter mainloop
        self.mouse = self.MouseHandler()
        self.mainloop()

    def handle_mouse_input(self):
        if self.mouse.in_rectangle(self.view_port_position):
            mx, my = self.mouse.pos
            point_x, point_y = mx - self.view_port_position[0][0], my - self.view_port_position[0][1]
            # TODO: Reduce redundancy here
            if self.mouse.current_mode == "camera":
                # In view port
                if self.mouse.mouse_motion and self.mouse.holding and self.mouse.in_rectangle(self.view_port_position):
                    move = self.mouse.get_instant_diff()
                    offset_x = -move[0] / self.view_port.zoom
                    offset_y = -move[1] / self.view_port.zoom
                    self.view_port.move_camera_by_vector(offset_x, offset_y)
                self._handle_scroll_wheel_zoom()
            elif self.mouse.current_mode == "bot-select":
                if self.mouse.mouse_button == 1:
                    self.world.selected_bot = None
                    # Get the mouse position relative to the view port
                    world_point = self.view_port.surface_point_to_world((point_x, point_y))
                    distances, indexes = self.world.kd_tree.query(world_point, k=15)
                    for distance, index in zip(distances, indexes):
                        entity = self.world.all_entities[index]
                        if isinstance(entity, Bot):
                            self.world.selected_bot = entity
                            print('Selecting bot near world point', world_point)
                            print('Selected', self.world.selected_bot, distance, 'from mouse point')
                            break
                elif self.mouse.mouse_button == 3:
                    if self.world.selected_bot:
                        print("Removing bot selection")
                        self.world.selected_bot = None
                # Allow zooming in and out even in bot selection mode
                self._handle_scroll_wheel_zoom()
        elif self.mouse.in_rectangle(self.info_panel_position):
            # In info panel
            pass

    def _handle_scroll_wheel_zoom(self):
        if self.mouse.mouse_button == 5:
            world_x, world_y = self.view_port.surface_point_to_world((self.view_port.width // 2,
                                                                      self.view_port.height // 2))
            self.view_port.zoom_out()
            self.view_port.center_camera_on_point((world_x, world_y))
        elif self.mouse.mouse_button == 4:
            world_x, world_y = self.view_port.surface_point_to_world((self.view_port.width // 2,
                                                                      self.view_port.height // 2))
            self.view_port.zoom_in()
            self.view_port.center_camera_on_point((world_x, world_y))

    def mainloop(self):
        while self.running:
            self.handle_user_input()
            self.handle_mouse_input()
            # Update the world
            if not self.paused:
                self.world.step()
                self.view_port.track_selected_bot()
                # Collect Data if enabled
                self.collect_data()
                self.tick += 1
            self.draw_graphics()
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
        self.mouse.mouse_button = None
        self.mouse.mouse_motion = False
        self.mouse.button_pressed = (0, 0, 0)
        for event in pygame.event.get():
            # Let the user quick the simulation
            if event.type == pygame.QUIT:
                self.running = 0
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_ESCAPE:
                    self.running = 0
                # Let the user pause the simulation
                elif key == pygame.K_SPACE:
                    self.paused = False if self.paused else True
                # Let the user control the camera using arrow keys
                elif key == pygame.K_LEFT:
                    self.view_port.move_camera_by_vector(-10, 0)
                elif key == pygame.K_RIGHT:
                    self.view_port.move_camera_by_vector(10, 0)
                elif key == pygame.K_UP:
                    self.view_port.move_camera_by_vector(0, -10)
                elif key == pygame.K_DOWN:
                    self.view_port.move_camera_by_vector(0, 10)
                elif key == pygame.K_0:
                    self.view_port.zoom = 1
                    x, y = 0, 0
                    if self.world.boundary_sizes:
                        x, y = self.world.boundary_sizes[0] / 2, self.world.boundary_sizes[1] / 2
                    self.view_port.center_camera_on_point((x, y))
                elif key == pygame.K_1:
                    self.mouse.change_mode("camera")
                    print("Entered 'camera' mode")
                elif key == pygame.K_2:
                    self.mouse.change_mode("bot-select")
                    print("Entered 'bot-select' mode")
                elif key == pygame.K_3:
                    # Save the intelligence graph of the selected bot
                    folder = os.getcwd() + os.sep + 'brain_graphs' + os.sep
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    if self.world.selected_bot:
                        print("Saving brain of currently selected bot...")
                        file = folder + "brain_" + str(
                            datetime.datetime.now().strftime("%y-%m-%d_%H-%M-%S_")) + self.world.selected_bot.name
                        WorldWatcher.save_bot_intelligence(self.world.selected_bot, file)
                    else:
                        print("Cannot save a brain if no bot is selected")
                elif key == pygame.K_4:
                    # Toggle rendering of signals in the view port
                    self.view_port.draw_signals = False if self.view_port.draw_signals else True
                    print("Toggled Signal rendering")
            # Handle mouse control
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse.mouse_button = event.button
                self.mouse.button_pressed = pygame.mouse.get_pressed()
                if event.button == 1:
                    self.mouse.set_click(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse.mouse_motion = True
                self.mouse.set_position(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse.set_release(event.pos)
            # Take care of window resizing
            elif event.type == pygame.VIDEORESIZE:
                self.attempt_window_rescale(event.w, event.h)

    def attempt_window_rescale(self, new_width, new_height):
        # TODO: This needs some major cleanup
        original_width = self.main_surface.get_width()
        original_height = self.main_surface.get_height()
        minimum_dimension = self.info_panel.width * 2
        if new_width > minimum_dimension and new_height > minimum_dimension:
            # Create a new master surface
            self.main_surface = pygame.display.set_mode((new_width, new_height),
                                                        pygame.DOUBLEBUF | pygame.RESIZABLE)
            # Resize panels to fit the new size
            side_panel_height = new_height - self.graph_panel.height
            self.info_panel.resize_surface((self.info_panel.width, side_panel_height))
            new_view_width = new_width - self.info_panel.width - self.bot_panel.width
            self.view_port.resize_surface((new_view_width, new_height - self.graph_panel.height))
            self.bot_panel.resize_surface((self.bot_panel.width, side_panel_height))
            graph_width = self.info_panel.width + self.bot_panel.width + self.view_port.width
            self.graph_panel.resize_surface((graph_width, self.graph_panel.height))
            # Set the new positions
            self.info_panel_position = ((0, 0), (self.info_panel.get_size()))
            self.view_port_position = ((self.info_panel.width, 0), self.view_port.get_size())
            self.bot_panel_position = ((self.info_panel.width + self.view_port.width, 0),
                                       (self.bot_panel.get_size()))
            self.graph_panel_position = ((0, self.info_panel.height), (graph_width, self.graph_panel.height))
            # Center the world if using boundaries
            if self.world.boundary_sizes:
                x, y = self.world.boundary_sizes
                self.view_port.center_camera_on_point((x / 2, y / 2))
        else:
            print("Cannot resize window to smaller than (%d, %d)" % (minimum_dimension, minimum_dimension))
            self.main_surface = pygame.display.set_mode((original_width, original_height),
                                                        pygame.DOUBLEBUF | pygame.RESIZABLE)

    def draw_graphics(self):
        # Draw the various views to the window
        self.view_port.render()
        # Draw a red "Paused" box around the view port if the simulation is paused
        if self.paused:
            thick = 1
            view = self.view_port.surface
            pygame.draw.rect(view, (200, 50, 50),
                             (1, 0, view.get_width() - (thick // 2) - 1, view.get_height() - (thick // 2)), thick)
        self.info_panel.render()
        self.bot_panel.render()
        self.graph_panel.render()
        self.main_surface.blit(self.view_port.surface, self.view_port_position[0])
        self.main_surface.blit(self.info_panel.surface, self.info_panel_position[0])
        self.main_surface.blit(self.bot_panel.surface, self.bot_panel_position[0])
        self.main_surface.blit(self.graph_panel.surface, self.graph_panel_position[0])
        # Draw a line separating the view port from the info view
        for panel, offset in ((self.info_panel_position, 1), (self.bot_panel_position, self.bot_panel_position[1][0])):
            line_start = (panel[0][0] + panel[1][0] - offset, panel[0][1])
            line_end = (line_start[0], line_start[1] + panel[1][1])
            pygame.draw.line(self.main_surface, (70, 70, 70), line_start, line_end, 2)
        # Draw a line between the graph and everything else
        pygame.draw.line(self.main_surface, (70, 70, 70), self.graph_panel_position[0],
                         (self.graph_panel.width, self.graph_panel_position[0][1]), 2)
        # Handle cursor graphics
        # TODO: Cursor icons only need to be changes with the cursor enters or exits a panel, not every frame
        if self.mouse.in_rectangle(self.view_port_position):
            size, hot_spot, cursor = self.mouse.modes[self.mouse.current_mode]
            pygame.mouse.set_cursor(size, hot_spot, *cursor)
        else:
            pygame.mouse.set_cursor(*pygame.cursors.arrow)
        # Apply any macro-level scaling
        final_surface = self.main_surface
        self.window.blit(final_surface, (0, 0))

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
        self.data_collector.poll_world_for_data()
        self.graph_panel.poll_data()

    class MouseHandler:
        def __init__(self):
            self.pos = (0, 0)
            self.holding = False
            self.hold_time = 0
            self.click_coordinates = (0, 0)
            self.release_coordinates = (0, 0)
            self.click_time = 0
            self.mouse_button = None
            self.mouse_motion = False
            self.button_pressed = (0, 0, 0)
            self.modes = {}
            # Make a dict of modes and their cursors with the hot-spot location
            names_and_files = (('camera', 'camera_cursor.txt'),
                               ('bot-select', 'bot-select_cursor.txt'))
            for mode_name, file_name in names_and_files:
                cursor_string, size, hot_spot = self._load_cursor("resources" + os.sep + file_name)
                cursor = pygame.cursors.compile(cursor_string, black='x', white='.')
                self.modes[mode_name] = (size, hot_spot, cursor)
            self.current_mode = "camera"

        def _load_cursor(self, file_name):
            folder = os.getcwd() + os.sep
            with open(folder + file_name) as cursor_file:
                lines = cursor_file.readlines()
                hot_y = int(lines.pop())
                hot_x = int(lines.pop())
                for i, line in enumerate(lines):
                    lines[i] = line.rstrip("\n")
                return lines, (len(lines[0]), len(lines)), (hot_x, hot_y)

        def change_mode(self, mode):
            if mode in self.modes:
                self.current_mode = mode
            else:
                raise ValueError("%s is not a registered mouse mode" % mode)

        def set_click(self, pos):
            self.click_coordinates = pos
            self.hold_time = 0
            self.click_time = time.time()
            self.holding = True
            pygame.mouse.get_rel()

        def set_release(self, pos):
            self.release_coordinates = pos
            self.hold_time = time.time() - self.click_time
            self.holding = False

        def set_position(self, pos):
            self.pos = pos

        def get_instant_diff(self):
            return pygame.mouse.get_rel()

        def get_drag_vector(self):
            dx = self.release_coordinates[0] - self.click_coordinates[0]
            dy = self.release_coordinates[1] - self.click_coordinates[1]
            # TODO: Finish this method

        def in_rectangle(self, rectangle):
            # Returns true if point is within rectangle, false otherwise
            point = self.pos
            x1 = rectangle[0][0]
            y1 = rectangle[0][1]
            x2 = x1 + rectangle[1][0]
            y2 = y1 + rectangle[1][1]
            return x1 <= point[0] <= x2 and y1 <= point[1] <= y2


# TODO: Allow selecting from multiple behavior files
if __name__ == '__main__':
    print("Starting Simulation...")
    earth = World(boundary_sizes=(380, 210), energy_pool=200000)
    basic_brain = create_basic_brain()
    minimal_brain = create_very_simple_brain()
    print("Controls:")
    print(" Camera Mode: Keyboard Key '1'")
    print("   Mouse wheel zoom, left drag to pan")
    print(" Bot-Select Mode: Keyboard Key '2'")
    print("   Left button to select")
    print("   Right button to de-select")
    print(" Space key to toggle Pause")
    print(" Keyboard Key '0': Recenter to original view")
    print(" Pressing Keyboard Key 3 with selected bot saves its brain")
    print(" Press Keyboard Key 4 to toggle Signal rendering")
    print("Legend:")
    print(" Filled green dot: Plant")
    print(" Filled purple dot: Bot")
    print(" Blue circles: Search Signals")
    print(" Green circles: 'Try to Eat Plants' Signal")
    print(" Red circles: 'Try to Eat Bots' Signal")
    print(" Yellow circles: 'Push Bots Away' Signal")
    print(" Have fun!")
    Simulation(earth, 400, 400, 200, fps=20, text_scale=2, graph_height=150, default_behavior=basic_brain,
               default_brain_size=10)
