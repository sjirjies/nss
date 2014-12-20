import copy
import functools


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

    def execute(self, bot):
        return self.function(bot)

    def __repr__(self):
        return str(self.node_number) + '_' + self.function.__name__


class StatementNode(BaseBehaviorNode):
    def __init__(self, function):
        super().__init__(function)
        self.next_node = None

    def assign_edge(self, next_node):
        self.next_node = next_node

    def execute(self, bot):
        super().execute(bot)
        return self.next_node


class ConditionalNode(BaseBehaviorNode):
    def __init__(self, function):
        super().__init__(function)
        self.true_node = None
        self.false_node = None

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
    # TODO: add methods for mutating the graph using the NodeRegister


