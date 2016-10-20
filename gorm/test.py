import unittest
from copy import deepcopy
import gorm


testkvs = [0, 1, 10, 10**10, 10**10**4, 'spam', 'eggs', 'ham',  '💧', '🔑', '𐦖',('spam', 'eggs', 'ham')]
testvs = [['spam', 'eggs', 'ham'], {'foo': 'bar', 0: 1, '💧': '🔑'}]
testdata = []
for k in testkvs:
    for v in testkvs:
        testdata.append((k, v))
    for v in testvs:
        testdata.append((k, v))
testdata.append(('lol', deepcopy(testdata)))


class GormTest(unittest.TestCase):
    def setUp(self):
        self.engine = gorm.ORM('sqlite:///:memory:')
        self.engine.initdb()
        self.graphmakers = (self.engine.new_graph, self.engine.new_digraph, self.engine.new_multigraph, self.engine.new_multidigraph)

    def tearDown(self):
        self.engine.close()


class GraphTest(GormTest):
    def setUp(self):
        super().setUp()
        g = self.engine.new_graph('test')
        g.add_node(0)
        self.assertIn(0, g)
        g.add_node(1)
        self.assertIn(1, g)
        g.add_edge(0, 1)
        self.assertIn(1, g.adj[0])
        self.assertIn(0, g.adj[1])
        # TODO: test adding edges whose nodes do not yet exist
        self.engine.rev = 1
        self.assertIn(0, g)
        self.assertIn(1, g)
        self.engine.branch = 'no_edge'
        self.assertIn(0, g)
        self.assertIn(1, g)
        self.assertIn(1, g.adj[0])
        self.assertIn(0, g.adj[1])
        g.remove_edge(0, 1)
        self.assertIn(0, g)
        self.assertIn(1, g)
        self.assertNotIn(0, g.adj[1])
        self.assertNotIn(1, g.adj[0])
        self.engine.branch = 'triangle'
        g.add_node(2)
        self.assertIn(2, g)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        g.add_edge(2, 0)
        self.engine.branch = 'square'
        self.engine.rev = 2
        self.assertIn(2, g)
        self.assertIn(2, list(g.node.keys()))
        g.remove_edge(2, 0)
        g.add_node(3)
        g.add_edge(2, 3)
        g.add_edge(3, 0)
        self.engine.branch = 'nothing'
        g.remove_nodes_from((0, 1, 2, 3))
        self.engine.branch = 'master'
        self.engine.rev = 0


class BranchLineageTest(GraphTest):
    def runTest(self):
        """Create some branches of history and check that gorm remembers where
        each came from and what happened in each.

        """
        self.assertTrue(self.engine.is_parent_of('master', 'no_edge'))
        self.assertTrue(self.engine.is_parent_of('master', 'triangle'))
        self.assertTrue(self.engine.is_parent_of('master', 'nothing'))
        self.assertTrue(self.engine.is_parent_of('no_edge', 'triangle'))
        self.assertTrue(self.engine.is_parent_of('square', 'nothing'))
        self.assertFalse(self.engine.is_parent_of('nothing', 'master'))
        self.assertFalse(self.engine.is_parent_of('triangle', 'no_edge'))
        g = self.engine.graph['test']
        self.assertIn(0, g.node)
        self.assertIn(1, g.node)
        self.assertIn(0, g.edge)
        self.assertIn(1, g.edge[0])
        self.engine.rev = 0

        def badjump():
            self.engine.branch = 'no_edge'
        self.assertRaises(ValueError, badjump)
        self.engine.rev = 2
        self.engine.branch = 'no_edge'
        self.assertIn(0, g)
        self.assertIn(0, list(g.node.keys()))
        self.assertNotIn(1, g.edge[0])
        self.assertRaises(KeyError, lambda: g.edge[0][1])
        self.engine.branch = 'triangle'
        self.assertIn(2, g.node)
        for orig in (0, 1, 2):
            for dest in (0, 1, 2):
                if orig == dest:
                    continue
                self.assertIn(orig, g.edge)
                self.assertIn(dest, g.edge[orig])
        self.engine.branch = 'square'
        self.assertNotIn(0, g.edge[2])
        self.assertRaises(KeyError, lambda: g.edge[2][0])
        self.engine.rev = 2
        self.assertIn(3, g.node)
        self.assertIn(1, g.edge[0])
        self.assertIn(2, g.edge[1])
        self.assertIn(3, g.edge[2])
        self.assertIn(0, g.edge[3])
        self.engine.branch = 'nothing'
        for node in (0, 1, 2):
            self.assertNotIn(node, g.node)
            self.assertNotIn(node, g.edge)
        self.engine.branch = 'master'
        self.engine.rev = 0
        self.assertIn(0, g.node)
        self.assertIn(1, g.node)
        self.assertIn(0, g.edge)
        self.assertIn(1, g.edge[0])


class StorageTest(GormTest):
    def runTest(self):
        """Test that all the graph types can store and retrieve key-value pairs
        for the graph as a whole, for nodes, and for edges.

        """
        for graphmaker in self.graphmakers:
            g = graphmaker('testgraph')
            g.add_node(0)
            g.add_node(1)
            g.add_edge(0, 1)
            n = g.node[0]
            e = g.edge[0][1]
            if isinstance(e, gorm.graph.MultiEdges):
                e = e[0]
            for (k, v) in testdata:
                g.graph[k] = v
                self.assertIn(k, g.graph)
                self.assertEqual(g.graph[k], v)
                del g.graph[k]
                self.assertNotIn(k, g.graph)
                n[k] = v
                self.assertIn(k, n)
                self.assertEqual(n[k], v)
                del n[k]
                self.assertNotIn(k, n)
                e[k] = v
                self.assertIn(k, e)
                self.assertEqual(e[k], v)
                del e[k]
                self.assertNotIn(k, e)
            self.engine.del_graph('testgraph')


class CompiledQueriesTest(GormTest):
    def runTest(self):
        """Make sure that the queries generated in SQLAlchemy are the same as
        those precompiled into SQLite.

        """
        from gorm.alchemy import Alchemist
        self.assertTrue(hasattr(self.engine.db, 'alchemist'))
        self.assertTrue(isinstance(self.engine.db.alchemist, Alchemist))
        from json import load
        with open(self.engine.db.json_path + '/sqlite.json', 'r') as jsonfile:
            precompiled = load(jsonfile)
        self.assertEqual(
            precompiled.keys(), self.engine.db.alchemist.sql.keys()
        )
        for (k, query) in precompiled.items():
            self.assertEqual(
                query,
                str(
                    self.engine.db.alchemist.sql[k]
                )
            )


if __name__ == '__main__':
    unittest.main()
