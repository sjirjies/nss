import os
import time
import pygame
from datetime import timedelta
from world import World, WorldWatcher

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


class ViewPort:
    def __init__(self, world, width, height):
        self.world = world
        self.surface_width = width
        self.surface_height = height
        self.surface = pygame.Surface((width, height))
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1

    def zoom_in(self):
        self.zoom += 1

    def zoom_out(self):
        if self.zoom >= 2:
            self.zoom -= 1

    def point_is_visible(self, point):
        visible_x = self.camera_x <= point[0] < (self.surface_width / self.zoom) + self.camera_x
        visible_y = self.camera_y <= point[1] < (self.surface_height / self.zoom) + self.camera_y
        return visible_x and visible_y

    def render(self):
        self.surface.fill((0, 0, 0))
        self.surface.lock()
        for signal in self.world.signals:
            # Make sure the signal is visible in the view before rendering it
            signal_in_camera_x = self.camera_x <= signal.x < (self.surface_width / self.zoom) + self.camera_x
            signal_in_camera_y = self.camera_y <= signal.y < (self.surface_height / self.zoom) + self.camera_y

            if signal_in_camera_x and signal_in_camera_y:
                diameter = signal.diameter
                left = ((signal.x - (diameter/2)) - self.camera_x) * self.zoom
                top = ((signal.y - (diameter/2)) - self.camera_y) * self.zoom
                signal_color = signal.color if signal.color else (75, 75, 75)
                pygame.draw.ellipse(self.surface, signal_color, (left, top, diameter*self.zoom, diameter*self.zoom), 1)
        self.surface.unlock()
        pixels = pygame.surfarray.pixels3d(self.surface)
        for entity_list in [self.world.plants, self.world.bots]:
            for entity in entity_list:
                # Make sure the entity is visible in the camera before bothering with rendering it
                if self.point_is_visible((entity.x, entity.y)):
                    entity_color = (255, 255, 255)
                    if isinstance(entity, Plant):
                        ratio = entity.energy/entity.max_energy
                        entity_color = (int(40 * ratio), int(240 * ratio), int(40 * ratio))
                    if isinstance(entity, Bot):
                        entity_color = (200, 40, 200)
                        if self.world.selected_bot and entity is self.world.selected_bot:
                            base_x = (entity.x-self.camera_x) * self.zoom
                            base_y = (entity.y-self.camera_y) * self.zoom
                            for border_x in (-1, 0, 1):
                                for border_y in (-1, 0, 1):
                                    px = base_x + border_x
                                    py = base_y + border_y
                                    pixels[px][py] = (255, 255, 255)
                    pixels[(entity.x-self.camera_x) * self.zoom][(entity.y-self.camera_y) * self.zoom] = entity_color
        del pixels
        
    def track_selected_bot(self):
        if self.world.selected_bot:
            bot = self.world.selected_bot
            self.center_camera_on_point((int(bot.x), int(bot.y)))

    def move_camera_to_coordinates(self, x, y):
        self.camera_x, self.camera_y = x, y

    def move_camera_by_vector(self, dx, dy):
        self.camera_x += dx
        self.camera_y += dy

    def get_center_offset(self):
        dx = (self.surface_width / (self.zoom + 1)) - self.camera_x
        dy = (self.surface_height / (self.zoom + 1)) - self.camera_y
        return dx, dy

    def center_camera_on_point(self, point):
        box_width, box_height = self.surface_width/self.zoom, self.surface_height/self.zoom
        half_width, half_height = box_width//2, box_height//2
        x = point[0] - half_width
        y = point[1] - half_height
        self.move_camera_to_coordinates(x, y)

    def point_to_world(self, point):
        world_x = (point[0] / self.zoom) + self.camera_x
        world_y = (point[1] / self.zoom) + self.camera_y
        return world_x, world_y


class BasePanel:
    def __init__(self, world, width, height, text_color, bg_color):
        self.text_color = text_color
        self.surface = pygame.Surface((width, height))
        # self.font = pygame.font.SysFont('calibri,dejavu sans,courier-new', 10)
        self.width, self.height = width, height
        self.world = world
        self.writer = TextWriter('nss_font_5x8.png', 5, 8, 1, 16)
        self.bg_color = bg_color


class InfoPanel(BasePanel):
    def __init__(self, world, clock, width, height, text_color, bg_color):
        super(InfoPanel, self).__init__(world, width, height, text_color, bg_color)
        self.width, self.height = width, height
        self.clock = clock
        self.labels_map = self._position_labels()
        self._position_labels()

    def _position_labels(self):
        x = 5
        y = 22
        labels = ["Tick", "Time", "FPS", "Free Energy", "Plants", "Bots", "Signals"]
        positions = []
        for index, label in enumerate(labels):
            positions.append((label, (x, (index+1)*y)))
        positions.insert(0, ("Metrics", (x, x)))
        return positions

    def render(self):
        data = self.poll_data()
        self.surface.fill(self.bg_color)
        for index, pair in enumerate(self.labels_map):
            label, pos = pair
            label_surface = self.writer.get_text_surface(label, self.text_color)
            # label_surface = self.font.render(label, 0, color)
            self.surface.blit(label_surface, pos)
            if index > 0:
                amount_surface = self.writer.get_text_surface(str(data[index-1]), self.text_color)
                # amount_surface = self.font.render(str(data[index-1]), 0, color)
                self.surface.blit(amount_surface, (11, pos[1]+11))

    def poll_data(self):
        data = []
        data.append(self.world.tick_number)
        seconds = int(self.world.time)
        data.append(str(timedelta(seconds=seconds)))
        data.append(round(self.clock.get_fps(), 2))
        if self.world.energy_pool is not None:
            data.append(self.world.energy_pool)
        else:
            data.append("Unlimited")
        data.append(len(self.world.plants))
        data.append(len(self.world.bots))
        data.append(len(self.world.signals))
        return data


class BotPanel(BasePanel):
    def __init__(self, world, width, height, text_color, bg_color):
        super(BotPanel, self).__init__(world, width, height, text_color, bg_color)
        self.labels_map = self._position_labels()

    def _position_labels(self):
        x = 7
        y = 22
        labels = ["Name", "Position", "Energy", "Peak Energy", "Birthday", "Age", "Children"]
        positions = []
        for index, label in enumerate(labels):
            positions.append((label, (x, (index+1)*y)))
        positions.insert(0, ("Selected Bot", (x, x)))
        return positions

    def render(self):
        data = self.poll_data()
        self.surface.fill(self.bg_color)
        for index, pair in enumerate(self.labels_map):
            label, pos = pair
            label_surface = self.writer.get_text_surface(label, self.text_color)
            # label_surface = self.font.render(label, 0, color)
            self.surface.blit(label_surface, pos)
            if index > 0:
                amount_surface = self.writer.get_text_surface(str(data[index-1]), self.text_color)
                # amount_surface = self.font.render(str(data[index-1]), 0, color)
                self.surface.blit(amount_surface, (11, pos[1]+11))

    def poll_data(self):
        if self.world.selected_bot:
            bot = self.world.selected_bot
            data = [bot.name, str((int(bot.x), int(bot.y))), bot.energy, bot.peak_energy,
                    bot.birthday, bot.age, bot.number_children]
            return data
        else:
            return ['-' for _ in range(8)]


class TextWriter:
    def __init__(self, filename, char_width, char_height, border_gap, chars_per_row):
        self.font_surface = pygame.image.load(os.getcwd() + os.sep + filename)
        self.char_height = char_height
        self.char_width = char_width
        self.char_border = border_gap
        self.chars_per_row = chars_per_row
        self.char_map = {}
        for i in range(32, 128):
            char_index = i-32
            row = char_index // self.chars_per_row
            col = char_index % self.chars_per_row
            x_coord = (self.char_border * (col + 1)) + (col * self.char_width)
            y_coord = (self.char_border * (row + 1)) + (row * self.char_height)
            self.char_map[chr(i)] = ((x_coord, y_coord, self.char_width, self.char_height))

    def get_text_surface(self, text, text_color):
        chars_surface = pygame.Surface(((len(text) * self.char_width) + len(text), self.char_height),
                                       depth=self.font_surface)
        for i, char in enumerate(text):
            if char in self.char_map:
                rect = self.char_map[char]
            else:
                rect = self.char_map[chr(127)]
            chars_surface.blit(self.font_surface, ((i * self.char_width) + i, 0,
                                                   self.char_width, self.char_height), rect)
        pixel_array = pygame.PixelArray(chars_surface)
        pixel_array.replace((0, 0, 0), text_color)
        return chars_surface


class Simulation:
    def __init__(self, world, plant_growth_ticks, initial_bots, initial_bot_energy, collect_data=True,
                 fps=20, scale=2, default_behavior=None):
        # Set an environment variable to center the pygame screen
        # TODO: Move display stuff into the View
        self.world = world
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        self.clock = pygame.time.Clock()
        # Set up the different views
        if world.boundary_sizes:
            view_port_width, view_port_height = world.boundary_sizes
        else:
            view_port_width, view_port_height = 300, 300
        self.view_port = ViewPort(self.world, view_port_width, view_port_height)
        panel_text_color = (220, 220, 220)
        panel_bg_color = (10, 10, 10)
        panel_width = 85
        self.info_panel = InfoPanel(self.world, self.clock, panel_width,
                                    view_port_height, panel_text_color, panel_bg_color)
        self.bot_panel = BotPanel(self.world, panel_width, view_port_height, panel_text_color, panel_bg_color)
        main_surface_width = view_port_width + self.info_panel.width + self.bot_panel.width
        main_surface_height = view_port_height
        self.info_panel_position = ((0, 0), (self.info_panel.width, self.info_panel.height))
        self.view_port_position = ((self.info_panel.width, 0),
                                   (self.view_port.surface_width, self.view_port.surface_height))
        self.bot_panel_position = ((self.view_port_position[0][0] + self.view_port_position[1][0], 0),
                                   (self.bot_panel.width, self.info_panel.height))
        self.main_surface = pygame.Surface((main_surface_width, main_surface_height))
        self.window_width, self.window_height = scale * main_surface_width, scale * main_surface_height
        # Create the simulation window
        self.window = pygame.display.set_mode((self.window_width, self.window_height), pygame.DOUBLEBUF)
        pygame.display.set_caption('NSS')
        self.paused = False
        self.running = True
        self.tick = 0
        self.scale = scale
        self.fps = fps
        if collect_data:
            self.data_collector = WorldWatcher(self.world)
        else:
            self.data_collector = None
        self.seed_plants(plant_growth_ticks)
        # Populate the world with bots
        print("Adding bots...")
        self.world.populate(initial_bots, initial_bot_energy, default_behavior, behavior_size=8)
        # TODO: Account for paused time in the WorldWatcher results
        # Create a mouse handler and enter mainloop
        self.mouse = self.MouseHandler(self.scale)
        self.mainloop()

    def handle_mouse_input(self):
        if self.mouse.in_rectangle(self.view_port_position):
            mx, my = self.mouse.pos
            point_x, point_y = mx - self.view_port_position[0][0], my - self.view_port_position[0][1]
            if self.mouse.mode == "camera":
                # In view port
                # Translate mouse relative to view port
                # TODO: Reduce redundancy here
                if self.mouse.mouse_button == 5:
                    world_x, world_y = self.view_port.point_to_world((self.view_port.surface_width//2,
                                                                      self.view_port.surface_height//2))
                    self.view_port.zoom_out()
                    self.view_port.center_camera_on_point((world_x, world_y))
                elif self.mouse.mouse_button == 4:
                    world_x, world_y = self.view_port.point_to_world((self.view_port.surface_width//2,
                                                                      self.view_port.surface_height//2))
                    self.view_port.zoom_in()
                    self.view_port.center_camera_on_point((world_x, world_y))
                if self.mouse.mouse_motion and self.mouse.holding and self.mouse.in_rectangle(self.view_port_position):
                    move = self.mouse.get_instant_diff()
                    offset_x = -move[0] / self.view_port.zoom
                    offset_y = -move[1] / self.view_port.zoom
                    self.view_port.move_camera_by_vector(offset_x, offset_y)
            elif self.mouse.mode == "bot-select":
                if self.mouse.mouse_button == 1:
                    self.world.selected_bot = None
                    # Get the mouse position relative to the view port
                    world_point = self.view_port.point_to_world((point_x, point_y))
                    distances, indexes = self.world.kd_tree.query(world_point, k=15)
                    for distance, index in zip(distances, indexes):
                        entity = self.world.all_entities[index]
                        if isinstance(entity, Bot):
                            self.world.selected_bot = entity
                            print('Selecting bot near world point', world_point)
                            print('Selecetd', self.world.selected_bot, distance, 'from mouse point')
                            break
        elif self.mouse.in_rectangle(self.info_panel_position):
                # In info panel
                pass

    def mainloop(self):
        while self.running:
            self.handle_user_input()
            self.handle_mouse_input()
            # Update the world
            if not self.paused:
                self.view_port.track_selected_bot()
                self.world.step()
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
        # TODO: Add check to find out which view the user clicked inside
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
                    self.view_port.move_camera_to_coordinates(0, 0)
                    self.view_port.zoom = 1
                elif key == pygame.K_1:
                    self.mouse.mode = "camera"
                    print("Entered 'camera' mode")
                elif key == pygame.K_2:
                    self.mouse.mode = "bot-select"
                    print("Entered 'bot-select' mode")
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

    def draw_graphics(self):
        # Draw the various views to the window
        self.view_port.render()
        # Draw a red "Paused" box around the view port if the simulation is paused
        if self.paused:
            thick = 1
            view = self.view_port.surface
            pygame.draw.rect(view, (200, 50, 50),
                             (1, 0, view.get_width()-(thick//2)-1, view.get_height()-(thick//2)), thick)
        self.info_panel.render()
        self.bot_panel.render()
        self.main_surface.blit(self.view_port.surface, self.view_port_position[0])
        self.main_surface.blit(self.info_panel.surface, self.info_panel_position[0])
        self.main_surface.blit(self.bot_panel.surface, self.bot_panel_position[0])
        # Draw a line separating the view port from the info view
        for panel, offset in ((self.info_panel_position, 1), (self.bot_panel_position, self.bot_panel_position[1][0])):
            line_start = (panel[0][0] + panel[1][0] - offset, panel[0][1])
            line_end = (line_start[0], line_start[1] + panel[1][1])
            pygame.draw.line(self.main_surface, (70, 70, 70), line_start, line_end, 2)
        pygame.draw.line(self.main_surface, (70, 70, 70), line_start, line_end, 2)
        final_surface = self.main_surface
        if self.scale > 1:
            width, height = self.main_surface.get_width() * self.scale, self.main_surface.get_height() * self.scale
            final_surface = pygame.Surface((width, height))
            pygame.transform.scale(self.main_surface, (width, height), final_surface)
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
        if self.data_collector:
            self.data_collector.poll_world_for_data()

    class MouseHandler:
        def __init__(self, scale):
            self.scale = scale
            self.pos = (0, 0)
            self.holding = False
            self.hold_time = 0
            self.click_coordinates = (0, 0)
            self.release_coordinates = (0, 0)
            self.click_time = 0
            self.mouse_button = None
            self.mouse_motion = False
            self.button_pressed = (0, 0, 0)
            self.mode = "camera"

        def _scale_coordinates(self, pos):
            return pos[0]//self.scale, pos[1]//self.scale

        def set_click(self, pos):
            self.click_coordinates = self._scale_coordinates(pos)
            self.hold_time = 0
            self.click_time = time.time()
            self.holding = True
            pygame.mouse.get_rel()

        def set_release(self, pos):
            self.release_coordinates = self._scale_coordinates(pos)
            self.hold_time = time.time() - self.click_time
            self.holding = False

        def set_position(self, pos):
            self.pos = self._scale_coordinates(pos)

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


if __name__ == '__main__':
    print("Starting Simulation...")
    earth = World(boundary_sizes=(250, 250), energy_pool=150000)
    start_behavior = create_basic_intelligence()
    Simulation(earth, 500, 500, 250, collect_data=True, fps=20, scale=2, default_behavior=start_behavior)