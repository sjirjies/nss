import os
import pygame
import datetime
import collections


class BasePanel:
    def __init__(self, width, height, text_scale, text_color, bg_color):
        self.text_color = text_color
        self.text_scale = text_scale
        self.surface = pygame.Surface((width, height))
        # self.font = pygame.font.SysFont('calibri,dejavu sans,courier-new', 10)
        self.width, self.height = width, height
        self.writer = TextWriter('resources' + os.sep + 'nss_font_5x8.png', 5, 8, 1, 16)
        self.bg_color = bg_color

    def resize_surface(self, new_size):
        self.surface = pygame.Surface(new_size)
        self.width, self.height = new_size

    def get_size(self):
        return self.width, self.height


class ViewPort(BasePanel):
    def __init__(self, world, width, height, text_scale=1, text_color=(220, 220, 220), bg_color=(0, 0, 0)):
        super(ViewPort, self).__init__(width, height, text_scale, text_color, bg_color)
        self.world = world
        self.surface = pygame.Surface((width, height))
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1
        self.draw_signals = True

    def zoom_in(self):
        self.zoom *= 2

    def zoom_out(self):
        if self.zoom >= 2:
            self.zoom //= 2

    def point_is_visible(self, point):
        visible_x = self.camera_x <= point[0] < (self.width / self.zoom) + self.camera_x
        visible_y = self.camera_y <= point[1] < (self.height / self.zoom) + self.camera_y
        return visible_x and visible_y

    def render(self):
        self.surface.fill(self.bg_color)
        self.surface.lock()
        pixels = pygame.surfarray.pixels3d(self.surface)
        # Draw a vague outline around the world if bounded
        if self.world.boundary_sizes:
            left, top = self.world_point_to_surface((0, 0))
            width, height = self.world.boundary_sizes[0] * self.zoom, self.world.boundary_sizes[1] * self.zoom
            pygame.draw.rect(self.surface, (15, 15, 15), (left, top, width+1, height+1), int(self.zoom**0.5))
        # TODO: Use HSV color space instead of RBG to simplify all of this
        if self.draw_signals:
            # TODO: Draw signals so they fade as their energy decreases
            for signal in self.world.signals:
                if self.point_is_visible((signal.x, signal.y)):
                    diameter = signal.diameter
                    left = ((signal.x - (diameter/2)) - self.camera_x) * self.zoom
                    top = ((signal.y - (diameter/2)) - self.camera_y) * self.zoom
                    signal_color = signal.color if signal.color else (75, 75, 75)
                    pygame.draw.ellipse(self.surface, signal_color,
                                        (left, top, diameter*self.zoom, diameter*self.zoom), 1)
        for plant in self.world.plants:
            if self.point_is_visible((plant.x, plant.y)):
                energy_ratio = plant.energy/plant.max_energy
                plant_energy_color = (int(40 * energy_ratio), int(240 * energy_ratio), int(40 * energy_ratio))
                age_ratio = plant.age/plant.max_age
                plant_age_color = (40 - int(20*age_ratio), 240 - int(200*age_ratio), 40 - int(20*age_ratio))
                self._draw_plant_or_bot(pixels, plant, plant_energy_color, plant_age_color, True)
        for bot in self.world.bots:
            if self.point_is_visible((bot.x, bot.y)):
                age_ratio = bot.age/bot.max_age
                if bot.age <= 10:
                    bot_age_color = (30, 40, 250)
                else:
                    bot_age_color = (220 - int(150*age_ratio), 60 - int(40*age_ratio), 220 - int(150*age_ratio))
                energy_ratio = 1000 - bot.energy
                bot_energy_color = (220, 60, 220) if bot.energy > 1000 \
                    else (220-int(energy_ratio*(200/1000)), 60-int(energy_ratio*(50/1000)), 220-int(energy_ratio*(200/1000)))
                self._draw_plant_or_bot(pixels, bot, bot_energy_color, bot_age_color, True)
        # Draw a selection outline if a bot is selected
        if self.world.selected_bot:
            self._draw_plant_or_bot(pixels, self.world.selected_bot, (255, 255, 255), (255, 255, 255), False)
        del pixels
        self.surface.unlock()

    def _draw_plant_or_bot(self, pixel_array, entity, entity_color, energy_color, selected_color):
        t = 0 if selected_color else 1
        diameter = self.zoom
        if not selected_color:
            diameter += 2
        if diameter == 3:
            diameter += 1
        x, y = self.world_point_to_surface((entity.x, entity.y))
        if self.zoom == 1:
            pixel_array[x][y] = entity_color
            if not selected_color:
                for border_x, border_y in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                    px = x + border_x
                    py = y + border_y
                    pixel_array[px][py] = (255, 255, 255)
        elif self.zoom <= 2:
            pygame.draw.rect(self.surface, entity_color, (x - diameter//2, y - diameter//2, diameter, diameter), t)
        elif 3 <= self.zoom < 8:
            pygame.draw.ellipse(self.surface, entity_color, (x - diameter//2, y - diameter//2, diameter, diameter), t)
        else:
            pygame.draw.ellipse(self.surface, entity_color, (x - diameter//2, y - diameter//2, diameter, diameter), t)
            pygame.draw.ellipse(self.surface, energy_color,
                                (x - diameter//4, y - diameter//4, diameter//2, diameter//2), 0)

    def track_selected_bot(self):
        if self.world.selected_bot:
            bot = self.world.selected_bot
            self.center_camera_on_point((bot.x, bot.y))

    def move_camera_to_coordinates(self, x, y):
        self.camera_x, self.camera_y = x, y

    def move_camera_by_vector(self, dx, dy):
        self.camera_x += dx
        self.camera_y += dy

    def get_center_offset(self):
        dx = (self.width / (self.zoom + 1)) - self.camera_x
        dy = (self.height / (self.zoom + 1)) - self.camera_y
        return dx, dy

    def center_camera_on_point(self, point):
        box_width, box_height = self.width/self.zoom, self.height/self.zoom
        half_width, half_height = box_width/2, box_height/2
        x = point[0] - half_width
        y = point[1] - half_height
        self.move_camera_to_coordinates(x, y)

    def surface_point_to_world(self, point):
        return (point[0] / self.zoom) + self.camera_x, (point[1] / self.zoom) + self.camera_y

    def world_point_to_surface(self, point):
        return (point[0]-self.camera_x) * self.zoom, (point[1]-self.camera_y) * self.zoom


class InfoPanel(BasePanel):
    def __init__(self, world, clock, width, height, text_scale, text_color, bg_color):
        super(InfoPanel, self).__init__(width, height, text_scale, text_color, bg_color)
        self.world = world
        self.clock = clock
        self.labels_map = self._position_labels()
        self._position_labels()

    def _position_labels(self):
        x = 5
        y = 22 * self.text_scale
        labels = ["Tick", "Time", "FPS", "Free Energy", "Plants", "Bots", "Signals"]
        positions = []
        for index, label in enumerate(labels):
            positions.append((label, (x, (index+1)*y)))
        positions.insert(0, ("Metrics", (x, x)))
        return positions

    def render(self):
        # TODO: Make this cleaner
        data = self._poll_data()
        self.surface.fill(self.bg_color)
        for index, pair in enumerate(self.labels_map):
            label, pos = pair
            label_surface = self.writer.get_text_surface(label, self.text_color)
            if self.text_scale > 1:
                new_width = label_surface.get_width() * self.text_scale
                new_height = label_surface.get_height() * self.text_scale
                label_surface = pygame.transform.scale(label_surface, (new_width, new_height))
            # label_surface = self.font.render(label, 0, color)
            self.surface.blit(label_surface, pos)
            if index > 0:
                amount_surface = self.writer.get_text_surface(str(data[index-1]), self.text_color)
                if self.text_scale > 1:
                    new_width = amount_surface.get_width() * self.text_scale
                    new_height = amount_surface.get_height() * self.text_scale
                    amount_surface = pygame.transform.scale(amount_surface, (new_width, new_height))
                # amount_surface = self.font.render(str(data[index-1]), 0, color)
                self.surface.blit(amount_surface, (11, pos[1]+(11*self.text_scale)))

    def _poll_data(self):
        data = []
        data.append(self.world.tick_number)
        seconds = int(self.world.time)
        data.append(str(datetime.timedelta(seconds=seconds)))
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
    def __init__(self, world, width, height, text_scale, text_color, bg_color):
        super(BotPanel, self).__init__(width, height, text_scale, text_color, bg_color)
        self.world = world
        self.labels_map = self._position_labels()

    def _position_labels(self):
        x = 7
        y = 22 * self.text_scale
        labels = ["Name", "Position", "Energy", "Peak Energy", "Generation", "Birthday", "Age", "Children",
                  "Brain Size"]
        positions = []
        for index, label in enumerate(labels):
            positions.append((label, (x, (index+1)*y)))
        positions.insert(0, ("Selected Bot", (x, x)))
        return positions

    def render(self):
        # TODO: Make this cleaner
        data = self._poll_data()
        self.surface.fill(self.bg_color)
        for index, pair in enumerate(self.labels_map):
            label, pos = pair
            label_surface = self.writer.get_text_surface(label, self.text_color)
            if self.text_scale > 1:
                new_width = label_surface.get_width() * self.text_scale
                new_height = label_surface.get_height() * self.text_scale
                label_surface = pygame.transform.scale(label_surface, (new_width, new_height))
            # label_surface = self.font.render(label, 0, color)
            self.surface.blit(label_surface, pos)
            if index > 0:
                amount_surface = self.writer.get_text_surface(str(data[index-1]), self.text_color)
                if self.text_scale > 1:
                    new_width = amount_surface.get_width() * self.text_scale
                    new_height = amount_surface.get_height() * self.text_scale
                    amount_surface = pygame.transform.scale(amount_surface, (new_width, new_height))
                # amount_surface = self.font.render(str(data[index-1]), 0, color)
                self.surface.blit(amount_surface, (11, pos[1]+(11 * self.text_scale)))

    def _poll_data(self):
        if self.world.selected_bot:
            bot = self.world.selected_bot
            data = [bot.name, str((int(bot.x), int(bot.y))), bot.energy, bot.peak_energy,
                    bot.generation_number, bot.birthday,
                    '%d (%d%%)' % (bot.age, int(bot.age/bot.max_age*100)),
                    bot.number_children, len(bot.behavior.behavior_nodes)]
            return data
        else:
            return ['-' for _ in range(9)]


class GraphPanel(BasePanel):
    # TODO: Reduce lag probably caused by this class
    def __init__(self, world_watcher, width, height, text_scale, text_color, bg_color):
        super(GraphPanel, self).__init__(width, height, text_scale, text_color, bg_color)
        self.world_watcher = world_watcher
        self.granularity = 1
        self.plants = collections.deque(maxlen=self.width)
        self.bots = collections.deque(maxlen=self.width)
        self.signals = collections.deque(maxlen=self.width)
        self.max_value = 1

    def _plot_line(self, array, color, thickness):
        x = 0
        for value in array:
            y = (self.height + 3) - (((value+1)/(self.max_value+1)) * self.height)
            # Make sure the maximum value is drawn on the graph
            if y <= 6:
                y = 6
            pygame.draw.rect(self.surface, color, (x-1, int(y)-4, 2, 2), 1)
            x += 1

    def render(self):
        self.surface.fill(self.bg_color)
        for array, color in ((self.plants, (40, 220, 40)),
                             (self.bots, (220, 40, 220)), (self.signals, (40, 40, 220))):
            self._plot_line(array, color, 2)

    def poll_data(self):
        if self.plants and self.bots and self.signals:
            self.max_value = max(max(self.plants), max(self.bots), max(self.signals))
        else:
            self.max_value = 1
        self.plants.append(self.world_watcher.plant_numbers[-1])
        self.bots.append(self.world_watcher.bot_numbers[-1])
        self.signals.append(self.world_watcher.signal_numbers[-1])

    def resize_surface(self, new_size):
        super().resize_surface(new_size)
        # Reset the size of each deque and repopulate it with data
        world_plants = self.world_watcher.plant_numbers
        world_bots = self.world_watcher.bot_numbers
        world_signals = self.world_watcher.signal_numbers
        self.plants = collections.deque(world_plants, self.width)
        self.bots = collections.deque(world_bots, self.width)
        self.signals = collections.deque(world_signals, self.width)


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
            self.char_map[chr(i)] = (x_coord, y_coord, self.char_width, self.char_height)

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
