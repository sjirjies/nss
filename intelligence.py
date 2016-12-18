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
    eligible_seed_conditions = []
    eligible_seed_statements = []
    required_seed_statements = []
    required_seed_conditionals = []


def statement(seed_eligible=True, seed_required=False):
    def dummy_statement(function):
        @functools.wraps(function)
        def dec(*args, **kwargs):
            # print("Function: %s" % function.__name__)
            return function(*args, **kwargs)
        NodeRegister.registered_statements.append(dec)
        if seed_eligible:
            NodeRegister.eligible_seed_statements.append(function)
        if seed_required:
            NodeRegister.required_seed_statements.append(function)
        return dec
    return dummy_statement


def conditional(seed_eligible=True, seed_required=False):
    def dummy_conditional(function):
        @functools.wraps(function)
        def dec(*args, **kwargs):
            # print("Function: %s" % function.__name__)
            return function(*args, **kwargs)
        NodeRegister.registered_conditionals.append(dec)
        if seed_eligible:
            NodeRegister.eligible_seed_conditions.append(function)
        if seed_required:
            NodeRegister.required_seed_conditionals.append(function)
        return dec
    return dummy_conditional


class BaseBehaviorNode:
    count = 0

    def __init__(self, function):
        self.function = function
        BaseBehaviorNode.count += 1
        self.node_number = BaseBehaviorNode.count
        self.node_type = None

    def execute(self, bot):
        return self.function(bot)

    def replace_edge(self, find_node, replace_with_node):
        return

    def points_to(self, node):
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

    def points_to(self, node):
        return self.next_node == node

    def replace_edge(self, find_node, replace_with_node):
        if self.next_node == find_node:
            self.next_node = replace_with_node

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

    def points_to(self, node):
        return self.true_node == node or self.false_node == node

    def replace_edge(self, find_node, replace_with_node):
        if self.true_node == find_node:
            self.true_node = replace_with_node
        if self.false_node == find_node:
            self.false_node = replace_with_node

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
        self.entry_node = None
        self.current_behavior_node = None

    def step(self, bot):
        if self.current_behavior_node is None:
            raise ValueError("Current node must be a function, not None. (Bot: %s)" % bot)
        self.current_behavior_node = self.current_behavior_node.execute(bot)

    def set_entry_node(self, entry_node):
        self.entry_node = entry_node
        self.current_behavior_node = entry_node

    def return_tree_copy(self):
        return copy.deepcopy(self)

    def generate_random_graph(self, number_of_nodes, percent_conditional=0.5):
        # First pick some random functions from the registry and create nodes from them
        self.behavior_nodes = []
        required_node_count = len(NodeRegister.required_seed_statements) + len(NodeRegister.required_seed_conditionals)
        for n in range(required_node_count):
            # Set a temporary node in case the following fails
            node = StatementNode(choice(NodeRegister.eligible_seed_statements))
            if NodeRegister.required_seed_conditionals and NodeRegister.required_seed_statements:
                if random() < percent_conditional:
                    node = ConditionalNode(choice(NodeRegister.required_seed_conditionals))
                else:
                    node = StatementNode(choice(NodeRegister.required_seed_statements))
            elif NodeRegister.required_seed_conditionals:
                node = ConditionalNode(choice(NodeRegister.required_seed_conditionals))
            elif NodeRegister.required_seed_statements:
                node = StatementNode(choice(NodeRegister.required_seed_statements))
            number_of_nodes -= 1
            self.behavior_nodes.append(node)
        if number_of_nodes > 0:
            for counter in range(0, number_of_nodes):
                if random() < percent_conditional:
                    node = ConditionalNode(choice(NodeRegister.eligible_seed_conditions))
                else:
                    node = StatementNode(choice(NodeRegister.eligible_seed_statements))
                self.behavior_nodes.append(node)
        # Now hook the nodes together randomly
        for node in self.behavior_nodes:
            if node.node_type == NodeRegister.statement:
                node.next_node = choice(self.behavior_nodes)
            else:
                node.true_node = choice(self.behavior_nodes)
                node.false_node = choice(self.behavior_nodes)
        # Now pic a random entry node
        self.set_entry_node(choice(self.behavior_nodes))

    def mutate_behavior(self):
        mutation_type = np.random.random_integers(0, 3)
        if mutation_type == 0:
            self._mutate_replace_function()
        elif mutation_type == 1:
            self._mutate_shuffle_outgoing_edge()
        elif mutation_type == 2:
            self._mutate_inject_node()
        else:
            self._mutate_remove_node(choice(self.behavior_nodes))

    def get_all_nodes_pointing_to(self, node, include_self=True):
        connected = []
        for n in self.behavior_nodes:
            if n.points_to(node):
                connected.append(n)
        if not include_self:
            connected[:] = [x for x in connected if x != node]
        return connected

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

    def _mutate_remove_node(self, node_to_remove):
        # Do not remove the node if it is the only one in the graph, just return False
        if len(self.behavior_nodes) == 1:
            return False
        self.behavior_nodes.remove(node_to_remove)
        incoming_nodes = self.get_all_nodes_pointing_to(node_to_remove, include_self=False)
        # Case of removing a statement node
        if node_to_remove.node_type == NodeRegister.statement:
            destination_node = node_to_remove.next_node
            if destination_node is not node_to_remove:
                if node_to_remove is self.entry_node:
                    self.set_entry_node(destination_node)
                for incoming in incoming_nodes:
                    incoming.replace_edge(find_node=node_to_remove, replace_with_node=destination_node)
            else:
                if node_to_remove is self.entry_node:
                    self.set_entry_node(choice(self.behavior_nodes))
                for incoming in incoming_nodes:
                    incoming.replace_edge(find_node=node_to_remove, replace_with_node=incoming)
        # Case of removing a conditional node
        elif node_to_remove.node_type == NodeRegister.conditional:
            true_node = node_to_remove.true_node
            false_node = node_to_remove.false_node
            if true_node is node_to_remove and false_node is node_to_remove:
                if node_to_remove is self.entry_node:
                    self.set_entry_node(choice(self.behavior_nodes))
                for incoming in incoming_nodes:
                    incoming.replace_edge(find_node=node_to_remove, replace_with_node=incoming)
            elif true_node is not node_to_remove and false_node is not node_to_remove:
                if node_to_remove is self.entry_node:
                    self.set_entry_node(choice([true_node, false_node]))
                for incoming in incoming_nodes:
                    incoming.replace_edge(find_node=node_to_remove, replace_with_node=choice([false_node, true_node]))
            else:
                next_node = true_node if true_node is not node_to_remove else false_node
                if node_to_remove is self.entry_node:
                    self.set_entry_node(next_node)
                for incoming in incoming_nodes:
                    incoming.replace_edge(find_node=node_to_remove, replace_with_node=next_node)
        return True
