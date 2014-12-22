import copy
import functools
from random import random, choice
import numpy as np


class NodeRegister:
    # statement and conditional are just used to ID functions
    statement = 1
    conditional = 2
    registered_statements = []
    registered_conditionals = []


def statement(function):
    @functools.wraps(function)
    def dec(*args, **kwargs):
        # print("Function: %s" % function.__name__)
        return function(*args, **kwargs)
    NodeRegister.registered_statements.append(dec)
    return dec


def conditional(function):
    @functools.wraps(function)
    def dec(*args, **kwargs):
        # print("Function: %s" % function.__name__)
        return function(*args, **kwargs)
    NodeRegister.registered_conditionals.append(dec)
    return dec


class BaseBehaviorNode:
    count = 0

    def __init__(self, function):
        self.function = function
        BaseBehaviorNode.count += 1
        self.node_number = BaseBehaviorNode.count
        self.node_type = None

    def execute(self, bot):
        return self.function(bot)

    def is_connected_to(self, node):
        return False


class StatementNode(BaseBehaviorNode):
    def __init__(self, function):
        super().__init__(function)
        self.next_node = None
        self.node_type = NodeRegister.statement

    def assign_edge(self, next_node):
        self.next_node = next_node

    def execute(self, bot):
        super().execute(bot)
        return self.next_node

    def is_connected_to(self, node):
        return self.next_node == node

    def __str__(self):
        if self.next_node is None:
            next_name = 'None'
        else:
            next_name = str(self.next_node.node_number) + '_' + self.next_node.function.__name__
        return str(self.node_number) + '_' + self.function.__name__ + ' -> ' + next_name


class ConditionalNode(BaseBehaviorNode):
    def __init__(self, function):
        super().__init__(function)
        self.true_node = None
        self.false_node = None
        self.node_type = NodeRegister.conditional

    def assign_edges(self, true_node, false_node):
        self.true_node = true_node
        self.false_node = false_node

    def execute(self, bot):
        result = super().execute(bot)
        if result is None:
            raise ValueError("Functions of conditional nodes must return True or False, not None.")
        if result:
            return self.true_node
        return self.false_node

    def is_connected_to(self, node):
        return self.true_node == node or self.false_node == node

    def __str__(self):
        if self.true_node is None:
            true_name = 'None'
        else:
            true_name = str(self.true_node.node_number) + '_' + self.true_node.function.__name__
        if self.false_node is None:
            false_name = 'None'
        else:
            false_name = str(self.false_node.node_number) + '_' + self.false_node.function.__name__
        return str(self.node_number) + '_' + self.function.__name__ + ' ? ' + true_name + ' : ' + false_name


class BehaviorGraph:
    def __init__(self):
        self.behavior_nodes = []
        self.current_behavior_node = None

    def step(self, bot):
        if self.current_behavior_node is None:
            raise ValueError("Current node must be a function, not None. (Bot: %s)" % bot)
        self.current_behavior_node = self.current_behavior_node.execute(bot)

    def return_tree_copy(self):
        return copy.deepcopy(self)

    def generate_random_graph(self):
        # TODO: Finish creating random graphs
        pass

    def mutate_behavior(self):
        mutation_type = np.random.random_integers(0, 3)
        if mutation_type == 0:
            self._mutate_replace_function()
        elif mutation_type == 1:
            self._mutate_shuffle_outgoing_edge()
        elif mutation_type == 2:
            self._mutate_inject_node()
        # else:
        #     self._mutate_remove_node()

    def _mutate_replace_function(self):
        node = choice(self.behavior_nodes)
        if node.node_type == NodeRegister.statement:
            random_function = choice(NodeRegister.registered_statements)
        elif node.node_type == NodeRegister.conditional:
            random_function = choice(NodeRegister.registered_conditionals)
        else:
            raise ValueError("Node %s has been discovered as neither a statement or condition." % node)
        node.function = random_function

    def _mutate_shuffle_outgoing_edge(self):
        node = choice(self.behavior_nodes)
        if node.node_type == NodeRegister.statement:
            node.next_node = choice(self.behavior_nodes)
        elif node.node_type == NodeRegister.conditional:
            # Make a choice to decide which edge to modify
            if random() < 0.5:
                node.true_node = choice(self.behavior_nodes)
            else:
                node.false_node = choice(self.behavior_nodes)
        else:
            raise ValueError("Node %s has been discovered as neither a statement or condition." % node)

    def _mutate_inject_node(self):
        previous = choice(self.behavior_nodes)
        # Make a choice to decide which type of node to inject
        new_node_type = choice((NodeRegister.statement, NodeRegister.conditional))
        # Injecting a statement in front of a statement
        if previous.node_type == NodeRegister.statement and new_node_type == NodeRegister.statement:
            new_node = StatementNode(choice(NodeRegister.registered_statements))
            new_node.assign_edge(previous.next_node)
            previous.next_node = new_node
        # Injecting a conditional in front of a statement
        elif previous.node_type == NodeRegister.statement and new_node_type == NodeRegister.conditional:
            new_node = ConditionalNode(choice(NodeRegister.registered_conditionals))
            if random() < 0.5:
                new_node.assign_edges(previous.next_node, choice(self.behavior_nodes))
            else:
                new_node.assign_edges(choice(self.behavior_nodes), previous.next_node)
            previous.next_node = new_node
        # Injecting a statement in front of a conditional
        elif previous.node_type == NodeRegister.conditional and new_node_type == NodeRegister.statement:
            new_node = StatementNode(choice(NodeRegister.registered_statements))
            if random() < 0.5:
                new_node.assign_edge(previous.true_node)
                previous.true_node = new_node
            else:
                new_node.assign_edge(previous.false_node)
                previous.false_node = new_node
        # Injecting a conditional in front of a conditional
        elif previous.node_type == NodeRegister.conditional and new_node_type == NodeRegister.conditional:
            new_node = ConditionalNode(choice(NodeRegister.registered_conditionals))
            if random() < 0.5:
                if random() < 0.5:
                    new_node.assign_edges(previous.true_node, choice(self.behavior_nodes))
                else:
                    new_node.assign_edges(choice(self.behavior_nodes), previous.true_node)
                previous.true_node = new_node
            else:
                if random() < 0.5:
                    new_node.assign_edges(previous.false_node, choice(self.behavior_nodes))
                else:
                    new_node.assign_edges(choice(self.behavior_nodes), previous.false_node)
                previous.false_node = new_node
        else:
            raise ValueError("Node %s has been detected as neither a statement or condition." % previous)
        self.behavior_nodes.append(new_node)

    def _mutate_remove_node(self):
        # TODO: Definitely unit test this one
        to_remove = choice(self.behavior_nodes)
        # Remove this node from the list of behavior nodes for ease of use later
        self.behavior_nodes.remove(to_remove)
        # Make sure we still have nodes left before going on
        if len(self.behavior_nodes) > 1:
            # Get a list of all nodes that have outgoing edges to the one we are removing
            connected = []
            for node in self.behavior_nodes:
                # Do not count the node as connected if it is the one we are removing
                if node.is_connected_to(to_remove) and node is not to_remove:
                    connected.append(node)
            # Deal with the case of removing a statement node
            if to_remove.node_type == NodeRegister.statement:
                # Dead with the case of a statement node leading to itself
                self_connected = False
                if to_remove.is_connected_to(to_remove):
                    self_connected = True
                # Randomly assign the incoming edges to other nodes (pretty wild) if to_remove is self connected
                # Otherwise, assign the edges to whatever to_remove points to
                for c in connected:
                    # Deal with the connected node being a statement or condition
                    if c.node_type == NodeRegister.statement:
                        # behavior_nodes no longer contains to_remove, so c should not connect to it.
                        # Here we connect c to to_remove's next node, but if to_remove points to self then a random node
                        c.next_node = choice(self.behavior_nodes) if self_connected else to_remove.next_node
                    else:
                        # Here c is conditional. Reassign any edge that points to to_remove
                        if c.true_node == to_remove:
                            c.true_node = choice(self.behavior_nodes) if self_connected else to_remove.next_node
                        if c.false_node == to_remove:
                            c.false_node = choice(self.behavior_nodes) if self_connected else to_remove.next_node
            else:
                # Now deal with the case of to_remove as a condition node
                # First case is true and false paths both point to self
                if to_remove.false_node == to_remove and to_remove.true_node == to_remove:
                    # In this case assign the incoming edges randomly
                    for c in connected:
                        if c.node_type == NodeRegister.statement:
                            c.next_node = choice(self.behavior_nodes)
                        else:
                            if c.true_node == to_remove:
                                c.true_node = choice(self.behavior_nodes)
                            if c.false_node == to_remove:
                                c.false_node = choice(self.behavior_nodes)
                # The second case is if neither path points to itself
                elif to_remove.false_node != to_remove and to_remove.true_node != to_remove:
                    # Then give each incoming edge either the true or false path
                    for c in connected:
                        if c.node_type == NodeRegister.statement:
                            c.next_node = choice((to_remove.true_node, to_remove.false_node))
                        else:
                            if c.true_node == to_remove:
                                c.true_node = choice((to_remove.true_node, to_remove.false_node))
                            if c.false_node == to_remove:
                                c.false_node = choice((to_remove.true_node, to_remove.false_node))
                # The last case is when one of the paths points to self and the other does not
                elif to_remove.false_node == to_remove and to_remove.true_node != to_remove:
                    for c in connected:
                        if c.node_type == NodeRegister.statement:
                            c.next_node = to_remove.true_node
                        else:
                            if c.true_node == to_remove:
                                c.true_node = to_remove.true_node
                            if c.false_node == to_remove:
                                c.false_node = to_remove.true_node
                elif to_remove.false_node != to_remove and to_remove.true_node == to_remove:
                    for c in connected:
                        if c.node_type == NodeRegister.statement:
                            c.next_node = to_remove.false_node
                        else:
                            if c.true_node == to_remove:
                                c.true_node = to_remove.false_node
                            if c.false_node == to_remove:
                                c.false_node = to_remove.false_node
        to_remove = None