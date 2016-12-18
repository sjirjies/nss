import unittest
from intelligence import *


class TestBehaviorGraphNodeRemoval(unittest.TestCase):
    def setUp(self):
        self.graph = BehaviorGraph()

    def test_removing_statement_node_with_no_incoming_edges(self):
        a = StatementNode(None)
        b = StatementNode(None)
        self.graph.behavior_nodes = [a, b]
        self.graph.set_entry_node(a)
        a.next_node = b
        self.graph._mutate_remove_node(a)
        self.assertNotIn(a, self.graph.behavior_nodes, "Removed a statement node should not keep it in the node list \
        if it has no incoming edges and points to another statement node")
        self.assertIn(b, self.graph.behavior_nodes, "Removing a statement node with no incoming edges should not \
        remove the statement node it points to")
        self.assertEqual(b, self.graph.entry_node, "Removing an entry point statement node without incoming edges \
        that points to another statement node should set the second statement node as the entry point")
        self.assertEqual(b, self.graph.current_behavior_node, "Removing an entry point statement node without incoming \
        edges that points to another statement node should set the second statement node as the current node")

