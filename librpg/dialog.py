"""
The :mod:`dialog` module contains Dialogs that can be displayed through
the use of MessageQueue, which is built-in MapModels. These dialogs
are a tool for displaying conversations, questions, etc.
"""

import pygame

from librpg.locals import *
from librpg.context import get_context_stack
from librpg.config import dialog_config as cfg
from librpg.config import graphics_config as g_cfg
from librpg.config import game_config as m_cfg
from librpg.config import menu_config
from librpg.virtualscreen import get_screen
from librpg.context import Context
from librpg.menu import Menu, Label, Panel, MenuController, ArrowCursor


def build_lines(text, box_width, font):
    lines = []
    words = text.split()
    cur_line = words[0]
    _, height = font.size(cur_line)

    for word in words[1:]:
        projected_line = cur_line + ' ' + word
        width, height = font.size(projected_line)
        if width > box_width:
            lines.append([height, cur_line])
            cur_line = word
        else:
            cur_line += ' ' + word
    lines.append([height, cur_line])
    return lines


def split_boxes(lines, box_height, line_spacing):
    boxes = []
    box_cur_height = lines[0][0]
    box = [lines[0]]

    for line in lines[1:]:
        if box_cur_height + line[0] + line_spacing > box_height:
            boxes.append(box)
            box_cur_height = line[0]
            box = [line]
        else:
            box.append(line)
            box_cur_height += line[0] + line_spacing
    if box:
        boxes.append(box)

    return boxes


class MessageDialog(Menu):

    """
    A MessageDialog is a simple message to be displayed on the screen.

    *text* is the string that will be displayed and *block_movement*
    tells the map whether the movement in the map should be blocked while
    the message is shown.
    """

    def __init__(self, text, block_movement=True):
        self.text = text
        self.block_movement = block_movement

        Menu.__init__(self, g_cfg.screen_width - 2 * cfg.border_width,
                            g_cfg.screen_height / 2 - 2 * cfg.border_width,
                            cfg.border_width,
                            g_cfg.screen_height / 2 + cfg.border_width,
                            bg=(0, 0, 0, 0))

        panel = Panel(self.width, self.height)
        self.add_widget(panel, (0, 0))

        font = self.theme.get_font(cfg.font_size)
        box_width = g_cfg.screen_width - 4 * cfg.border_width
        lines = build_lines(self.text,
                            box_width,
                            font)

        # Draw message
        y_acc = 0
        for line in lines:
            label = Label(line[1])
            panel.add_widget(label,
                             (cfg.border_width,
                              cfg.border_width + y_acc))
            y_acc += line[0] + cfg.line_spacing

    def process_event(self, event):
        if event.type == KEYDOWN:
            if event.key in m_cfg.key_action:
                self.close()
        return self.block_movement


class ElasticMessageDialog(Menu):

    """
    Same as a MessageDialog but resizes the box as needed for the text to
    fit in.
    """

    def __init__(self, text, block_movement=True):
        self.text = text
        self.block_movement = block_movement

        # Split into lines
        font = menu_config.theme.get_font(cfg.font_size)
        box_width = g_cfg.screen_width - 4 * cfg.border_width
        lines = build_lines(self.text,
                            box_width,
                            font)

        # Calculate box size
        self.box_height = (sum([line[0] for line in lines])
                           + (len(lines) - 1) * cfg.line_spacing
                           + 4 * cfg.border_width)
        assert self.box_height < g_cfg.screen_height,\
               'Too much text for one box.'

        Menu.__init__(self, g_cfg.screen_width - 2 * cfg.border_width,
                            self.box_height - 2 * cfg.border_width,
                            cfg.border_width,
                            g_cfg.screen_height - self.box_height\
                            + cfg.border_width,
                            bg=(0, 0, 0, 0))

        panel = Panel(self.width, self.height)
        self.add_widget(panel, (0, 0))

        # Draw message
        y_acc = 0
        for line in lines:
            label = Label(line[1])
            panel.add_widget(label,
                             (cfg.border_width,
                              cfg.border_width + y_acc))
            y_acc += line[0] + cfg.line_spacing

    def process_event(self, event):
        if event.type == KEYDOWN:
            if event.key in m_cfg.key_action:
                self.close()
        return self.block_movement


class MultiMessageDialog(Menu):

    """
    Same as a MessageDialog but splits messages bigger than the default
    box size into multiple dialogs.
    """

    def __init__(self, text, block_movement=True):
        self.text = text
        self.block_movement = block_movement
        self.current_panel = None

        Menu.__init__(self, g_cfg.screen_width - 2 * cfg.border_width,
                            g_cfg.screen_height / 2 - 2 * cfg.border_width,
                            cfg.border_width,
                            g_cfg.screen_height / 2 + cfg.border_width,
                            bg=(0, 0, 0, 0))

        # Split into lines
        font = self.theme.get_font(cfg.font_size)
        box_width = g_cfg.screen_width - 4 * cfg.border_width
        lines = build_lines(self.text,
                            box_width,
                            font)

        # Split into boxes
        box_height = g_cfg.screen_height / 2 - 4 * cfg.border_width
        self.boxes = split_boxes(lines, box_height, cfg.line_spacing)
        self.panels = []

        # Draw panels
        for box in self.boxes:
            panel = Panel(self.width, self.height)
            y_acc = 0
            for line in box:
                label = Label(line[1])
                panel.add_widget(label,
                                 (cfg.border_width,
                                  cfg.border_width + y_acc))
                y_acc += line[0] + cfg.line_spacing
            self.panels.append(panel)

        self.advance_panel()

    def advance_panel(self):
        if self.current_panel is not None:
            self.remove_widget(self.current_panel)
            self.current_panel = None
        if self.panels:
            self.current_panel = self.panels.pop(0)
            self.add_widget(self.current_panel, (0, 0))

    def process_event(self, event):
        if event.type == KEYDOWN:
            if event.key in m_cfg.key_action:
                self.advance_panel()
                if self.current_panel is None:
                    self.close()
        return self.block_movement


class ChoiceDialog(Menu):

    """
    A ChoiceDialog is a message that comes along a list of options from
    which the player has to pick one option.

    *text* is the string that will be displayed and *block_movement*
    tells the map whether the movement in the map should be blocked while
    the message is shown.

    *choices* is a list of the options, which should be strings.
    """

    def __init__(self, text, choices, block_movement=True):
        self.block_movement = block_movement
        self.text = text
        self.choices = choices

        Menu.__init__(self, g_cfg.screen_width - 2 * cfg.border_width,
                            g_cfg.screen_height / 2 - 2 * cfg.border_width,
                            cfg.border_width,
                            g_cfg.screen_height / 2 + cfg.border_width,
                            bg=(0, 0, 0, 0))

        panel = Panel(self.width, self.height)
        self.add_widget(panel, (0, 0))

        # Build lines and choice lines
        font = self.theme.get_font(cfg.font_size)
        self.__build_lines(font)

        # Draw message
        y_acc = 0
        for line in self.lines:
            label = Label(line[1], focusable=False)
            panel.add_widget(label,
                             (cfg.border_width,
                              cfg.border_width + y_acc))
            y_acc += line[0] + cfg.line_spacing

        self.starting_option = None
        for line in self.choice_lines:
            label = Label(line[1], focusable=True)
            panel.add_widget(label,
                             (2 * cfg.border_width,
                              cfg.border_width + y_acc))
            y_acc += line[0] + cfg.choice_line_spacing
            if self.starting_option is None:
                self.starting_option = label

        ArrowCursor().bind(self, self.starting_option)

    def __build_lines(self, font):
        box_width = self.width - 2 * cfg.border_width
        self.lines = build_lines(self.text,
                                 box_width,
                                 font)

        box_width = self.width - 3 * cfg.border_width
        self.choice_lines = []
        for choice in self.choices:
            choice_line = build_lines(choice,
                                      box_width,
                                      font)
            self.choice_lines.extend(choice_line)

    def process_event(self, event):
        if event.type == KEYDOWN:
            if event.key in m_cfg.key_action:
                self.close()
            if event.key in m_cfg.key_left or event.key in m_cfg.key_right:
                return True
        return self.block_movement


class MessageQueue(Context):

    def __init__(self, parent=None):
        Context.__init__(self, parent)
        self.current = None
        self.controller = None
        self.queue = []

    def is_busy(self):
        return self.current is not None and self.current.block_movement

    def is_active(self):
        return self.current is not None

    def pop_next(self):
        if self.current is None and self.queue:
            self.current = self.queue.pop(0)
            self.controller = MenuController(self.current)
            get_context_stack().stack_context(self.controller)

    def push(self, message):
        self.queue.append(message)

    def update(self):
        if self.controller is not None and self.controller.is_done():
            self.current = None
        self.pop_next()
        return False
