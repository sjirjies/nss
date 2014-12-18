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
        return function(*args, **kwargs)

    NodeRegister.registered_statements.append(dec)
    return dec


def conditional(function):
    @functools.wraps(function)
    def dec(*args, **kwargs):
        return function(*args, **kwargs)

    NodeRegister.registered_conditionals.append(dec)
    return dec


class BehaviorNode:
    def __init__(self, function):
        self.function = function
        self.node_type = self._assign_node_type()
        self.next_node = None
        self.true_node = None
        self.false_node = None

    def execute(self, bot):
        result = self.function(bot)
        if self.node_type == NodeRegister.statement:
            return self.next_node
        elif self.node_type == NodeRegister.conditional:
            if result:
                return self.true_node
            return self.false_node

    def _assign_node_type(self):
        if self.function in NodeRegister.registered_statements:
            return NodeRegister.statement
        elif self.function in NodeRegister.registered_conditionals:
            return NodeRegister.conditional
        else:
            raise LookupError("Function %s is not registered as a statement or condition" % self.function)

    def __repr__(self):
        return self.function.__name__


class BehaviorTree:
    def __init__(self):
        self.behavior_nodes = []
        self.current_behavior_node = None

    def step(self, bot):
        if self.current_behavior_node is None:
            raise ValueError("Current Node Must be a function, not None. (Bot: %s)" % bot)
        self.current_behavior_node = self.current_behavior_node.execute(bot)

    def return_tree_copy(self):
        return copy.deepcopy(self)

    def generate_random_tree(self):
        pass