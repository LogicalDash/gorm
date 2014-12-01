# This file is part of gorm, an object relational mapper for versioned graphs.
# Copyright (C) 2014 Zachary Spector.
from sqlalchemy import (
    Table,
    Index,
    Column,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    Boolean,
    String,
    MetaData,
    ForeignKey,
    select,
    func,
    and_,
    null
)
from sqlalchemy.sql import bindparam
from sqlalchemy.sql.ddl import CreateTable, CreateIndex
from sqlalchemy import create_engine
from json import dumps

length = 50

meta = MetaData()

table_global = Table(
    'global', meta,
    Column('key', String(length), primary_key=True),
    Column('value', String(length), nullable=True)
)

table_branches = Table(
    'branches', meta,
    Column('branch', String(length), ForeignKey('branches.parent'),
           primary_key=True, default='master'
           ),
    Column('parent', String(length), default='master'),
    Column('parent_rev', Integer, default=0)
)

table_graphs = Table(
    'graphs', meta,
    Column('graph', String(length), primary_key=True),
    Column('type', String(length), default='Graph'),
    CheckConstraint(
        "type IN ('Graph', 'DiGraph', 'MultiGraph', 'MultiDiGraph')"
    )
)

table_graph_val = Table(
    'graph_val', meta,
    Column('graph', String(length), ForeignKey('graphs.graph'),
           primary_key=True),
    Column('key', String(length), primary_key=True),
    Column('branch', String(length), ForeignKey('branches.branch'),
           primary_key=True, default='master'),
    Column('rev', Integer, primary_key=True, default=0),
    Column('value', String(length), nullable=True)
)

index_graph_val = Index(
    "graph_val_idx",
    table_graph_val.c.graph,
    table_graph_val.c.key
)

table_nodes = Table(
    'nodes', meta,
    Column('graph', String(length), ForeignKey('graphs.graph'),
           primary_key=True),
    Column('node', String(length), primary_key=True),
    Column('branch', String(length), ForeignKey('branches.branch'),
           primary_key=True, default='master'),
    Column('rev', Integer, primary_key=True, default=0),
    Column('extant', Boolean)
)

index_nodes = Index(
    "nodes_idx",
    table_nodes.c.graph,
    table_nodes.c.node
)

table_node_val = Table(
    'node_val', meta,
    Column('graph', String(length), primary_key=True),
    Column('node', String(length), primary_key=True),
    Column('key', String(length), primary_key=True),
    Column('branch', String(length), ForeignKey('branches.branch'),
           primary_key=True, default='master'),
    Column('rev', Integer, primary_key=True, default=0),
    Column('value', String(length), nullable=True),
    ForeignKeyConstraint(['graph', 'node'], ['nodes.graph', 'nodes.node'])
)

index_node_val = Index(
    "node_val_idx",
    table_node_val.c.graph,
    table_node_val.c.node
)

table_edges = Table(
    'edges', meta,
    Column('graph', String(length), ForeignKey('graphs.graph'),
           primary_key=True),
    Column('nodeA', String(length), primary_key=True),
    Column('nodeB', String(length), primary_key=True),
    Column('idx', Integer, primary_key=True),
    Column('branch', String(length), ForeignKey('branches.branch'),
           primary_key=True, default='master'),
    Column('rev', Integer, primary_key=True, default=0),
    Column('extant', Boolean),
    ForeignKeyConstraint(['graph', 'nodeA'], ['nodes.graph', 'nodes.node']),
    ForeignKeyConstraint(['graph', 'nodeB'], ['nodes.graph', 'nodes.node'])
)

index_edges = Index(
    "edges_idx",
    table_edges.c.graph,
    table_edges.c.nodeA,
    table_edges.c.nodeB,
    table_edges.c.idx
)

table_edge_val = Table(
    'edge_val', meta,
    Column('graph', String(length), primary_key=True),
    Column('nodeA', String(length), primary_key=True),
    Column('nodeB', String(length), primary_key=True),
    Column('idx', Integer, primary_key=True),
    Column('key', String(length), primary_key=True),
    Column('branch', String(length), ForeignKey('branches.branch'),
           primary_key=True, default='master'),
    Column('rev', Integer, primary_key=True, default=0),
    Column('value', String(length), nullable=True),
    ForeignKeyConstraint(
        ['graph', 'nodeA', 'nodeB', 'idx'],
        ['edges.graph', 'edges.nodeA', 'edges.nodeB', 'edges.idx']
    )
)

index_edge_val = Index(
    "edge_val_idx",
    table_edge_val.c.graph,
    table_edge_val.c.nodeA,
    table_edge_val.c.nodeB,
    table_edge_val.c.idx,
    table_edge_val.c.key
)

table = {
    'global': table_global,
    'branches': table_branches,
    'graphs': table_graphs,
    'graph_val': table_graph_val,
    'nodes': table_nodes,
    'node_val': table_node_val,
    'edges': table_edges,
    'edge_val': table_edge_val
}

index = {
    'graph_val': index_graph_val,
    'nodes': index_nodes,
    'node_val': index_node_val,
    'edges': index_edges,
    'edge_val': index_edge_val
}


def compile_sql(dialect):
    def hirev_nodes_join(wheres):
        hirev = select(
            [
                table_nodes.c.graph,
                table_nodes.c.node,
                table_nodes.c.branch,
                func.MAX(table_nodes.c.rev).label('rev')
            ]
        ).where(and_(*wheres)).group_by(
            table_nodes.c.graph,
            table_nodes.c.node,
            table_nodes.c.branch
        ).alias('hirev')
        return table_nodes.join(
            hirev,
            and_(
                table_nodes.c.graph == hirev.c.graph,
                table_nodes.c.node == hirev.c.node,
                table_nodes.c.branch == hirev.c.branch,
                table_nodes.c.rev == hirev.c.rev
            )
        )

    def hirev_graph_val_join(wheres):
        hirev = select(
            [
                table_graph_val.c.graph,
                table_graph_val.c.key,
                table_graph_val.c.branch,
                func.MAX(table_graph_val.c.rev).label('rev')
            ]
        ).where(and_(*wheres)).group_by(
            table_graph_val.c.graph,
            table_graph_val.c.key,
            table_graph_val.c.branch
        ).alias('hirev')
        return table_graph_val.join(
            hirev,
            and_(
                table_graph_val.c.graph == hirev.c.graph,
                table_graph_val.c.key == hirev.c.key,
                table_graph_val.c.branch == hirev.c.branch,
                table_graph_val.c.rev == hirev.c.rev
            )
        )

    def node_val_hirev_join(wheres):
        hirev = select(
            [
                table_node_val.c.graph,
                table_node_val.c.node,
                table_node_val.c.branch,
                table_node_val.c.key,
                func.MAX(table_node_val.c.rev).label('rev')
            ]
        ).where(and_(*wheres)).group_by(
            table_node_val.c.graph,
            table_node_val.c.node,
            table_node_val.c.branch,
            table_node_val.c.key
        ).alias('hirev')

        return table_node_val.join(
            hirev,
            and_(
                table_node_val.c.graph == hirev.c.graph,
                table_node_val.c.node == hirev.c.node,
                table_node_val.c.key == hirev.c.key,
                table_node_val.c.branch == hirev.c.branch,
                table_node_val.c.rev == hirev.c.rev
            )
        )

    def edges_recent_join(wheres=None):
        hirev = select(
            [
                table_edges.c.graph,
                table_edges.c.nodeA,
                table_edges.c.nodeB,
                table_edges.c.idx,
                table_edges.c.branch,
                func.MAX(table_edges.c.rev).label('rev')
            ]
        )
        if wheres:
            hirev = hirev.where(and_(*wheres))
        hirev = hirev.group_by(
            table_edges.c.graph,
            table_edges.c.nodeA,
            table_edges.c.nodeB,
            table_edges.c.idx,
            table_edges.c.branch
        ).alias('hirev')
        return table_edges.join(
            hirev,
            and_(
                table_edges.c.graph == hirev.c.graph,
                table_edges.c.nodeA == hirev.c.nodeA,
                table_edges.c.nodeB == hirev.c.nodeB,
                table_edges.c.idx == hirev.c.idx,
                table_edges.c.branch == hirev.c.branch,
                table_edges.c.rev == hirev.c.rev
            )
        )

    def edge_val_recent_join(wheres=None):
        hirev = select(
            [
                table_edge_val.c.graph,
                table_edge_val.c.nodeA,
                table_edge_val.c.nodeB,
                table_edge_val.c.idx,
                table_edge_val.c.key,
                table_edge_val.c.branch,
                func.MAX(table_edge_val.c.rev).label('rev')
            ]
        )
        if wheres:
            hirev = hirev.where(
                and_(*wheres)
            )
        hirev = hirev.group_by(
            table_edge_val.c.graph,
            table_edge_val.c.nodeA,
            table_edge_val.c.nodeB,
            table_edge_val.c.idx,
            table_edge_val.c.key,
            table_edge_val.c.branch
        ).alias('hirev')
        return table_edge_val.join(
            hirev,
            and_(
                table_edge_val.c.graph == hirev.c.graph,
                table_edge_val.c.nodeA == hirev.c.nodeA,
                table_edge_val.c.nodeB == hirev.c.nodeB,
                table_edge_val.c.idx == hirev.c.idx,
                table_edge_val.c.branch == hirev.c.branch,
                table_edge_val.c.rev == hirev.c.rev
            )
        )

    r = {
        'ctbranch': select(
            [func.COUNT(table_branches.c.branch)]
        ).where(
            table_branches.c.branch == bindparam('branch')
        ).compile(dialect=dialect),
        'ctgraph': select(
            [func.COUNT(table_graphs.c.graph)]
        ).where(
            table_graphs.c.graph == bindparam('graph')
        ).compile(dialect=dialect),
        'allbranch': select(
            [
                table_branches.c.branch,
                table_branches.c.parent,
                table_branches.c.parent_rev
            ]
        ).compile(dialect=dialect),
        'global_get': select(
            [table_global.c.value]
        ).where(
            table_global.c.key == bindparam('key')
        ).compile(dialect=dialect),
        'edge_val_ins': table_edge_val.insert().values(
            graph=bindparam('graph'),
            nodeA=bindparam('orig'),
            nodeB=bindparam('dest'),
            idx=bindparam('idx'),
            key=bindparam('key'),
            branch=bindparam('branch'),
            rev=bindparam('rev'),
            value=bindparam('value')
        ).compile(dialect=dialect),
        'edge_val_upd': table_edge_val.update().values(
            value=bindparam('value')
        ).where(
            and_(
                table_edge_val.c.graph == bindparam('graph'),
                table_edge_val.c.nodeA == bindparam('orig'),
                table_edge_val.c.nodeB == bindparam('dest'),
                table_edge_val.c.idx == bindparam('idx'),
                table_edge_val.c.branch == bindparam('branch'),
                table_edge_val.c.rev == bindparam('rev')
            )
        ).compile(dialect=dialect),
        'global_items': select(
            [
                table_global.c.key,
                table_global.c.value
            ]
        ).compile(dialect=dialect),
        'ctglobal': select(
            [func.COUNT(table_global.c.key)]
        ).compile(dialect=dialect),
        'new_graph': table_graphs.insert().values(
            graph=bindparam('graph'),
            type=bindparam('type')
        ).compile(dialect=dialect),
        'graph_type': select(
            [table_graphs.c.type]
        ).where(
            table_graphs.c.graph == bindparam('graph')
        ).compile(dialect=dialect),
        'new_branch': table_branches.insert().values(
            branch=bindparam('branch'),
            parent=bindparam('parent'),
            parent_rev=bindparam('parent_rev')
        ).compile(dialect=dialect),
        'del_edge_val_graph': table_edge_val.delete().where(
            table_edge_val.c.graph == bindparam('graph')
        ).compile(dialect=dialect),
        'del_node_val_graph': table_node_val.delete().where(
            table_node_val.c.graph == bindparam('graph')
        ).compile(dialect=dialect),
        'del_node_graph': table_nodes.delete().where(
            table_nodes.c.graph == bindparam('graph')
        ).compile(dialect=dialect),
        'del_graph': table_graphs.delete().where(
            table_graphs.c.graph == bindparam('graph')
        ).compile(dialect=dialect),
        'parrev': select(
            [table_branches.c.parent_rev]
        ).where(
            table_branches.c.branch == bindparam('branch')
        ).compile(dialect=dialect),
        'parparrev': select(
            [table_branches.c.parent, table_branches.c.parent_rev]
        ).where(
            table_branches.c.branch == bindparam('branch')
        ).compile(dialect=dialect),
        'global_ins': table_global.insert().values(
            key=bindparam('key'),
            value=bindparam('value')
        ).compile(dialect=dialect),
        'global_upd': table_global.update().values(
            value=bindparam('value')
        ).where(
            table_global.c.key == bindparam('key')
        ),
        'global_del': table_global.delete().where(
            table_global.c.key == bindparam('key')
        ).compile(dialect=dialect),
        'nodes_extant': select(
            [table_nodes.c.node]
        ).select_from(
            hirev_nodes_join(
                [
                    table_nodes.c.graph == bindparam('graph'),
                    table_nodes.c.branch == bindparam('branch'),
                    table_nodes.c.rev <= bindparam('rev')
                ]
            )
        ).where(
            table_nodes.c.extant
        ).compile(dialect=dialect),
        'node_exists': select(
            [table_nodes.c.extant]
        ).select_from(
            hirev_nodes_join(
                [
                    table_nodes.c.graph == bindparam('graph'),
                    table_nodes.c.node == bindparam('node'),
                    table_nodes.c.branch == bindparam('branch'),
                    table_nodes.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'exist_node_ins': table_nodes.insert().values(
            graph=bindparam('graph'),
            node=bindparam('node'),
            branch=bindparam('branch'),
            rev=bindparam('rev'),
            extant=bindparam('extant')
        ).compile(dialect=dialect),
        'exist_node_upd': table_nodes.update().values(
            extant=bindparam('extant')
        ).where(
            and_(
                table_nodes.c.graph == bindparam('graph'),
                table_nodes.c.node == bindparam('node'),
                table_nodes.c.branch == bindparam('branch'),
                table_nodes.c.rev == bindparam('rev')
            )
        ).compile(dialect=dialect),
        'graph_val_items': select(
            [
                table_graph_val.c.key,
                table_graph_val.c.value
            ]
        ).select_from(
            hirev_graph_val_join(
                [
                    table_graph_val.c.graph == bindparam('graph'),
                    table_graph_val.c.branch == bindparam('branch'),
                    table_graph_val.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'graph_val_get': select(
            [
                table_graph_val.c.value
            ]
        ).select_from(
            hirev_graph_val_join(
                [
                    table_graph_val.c.graph == bindparam('graph'),
                    table_graph_val.c.key == bindparam('key'),
                    table_graph_val.c.branch == bindparam('branch'),
                    table_graph_val.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'graph_val_ins': table_graph_val.insert().values(
            graph=bindparam('graph'),
            key=bindparam('key'),
            branch=bindparam('branch'),
            rev=bindparam('rev'),
            value=bindparam('value')
        ).compile(dialect=dialect),
        'graph_val_upd': table_graph_val.update().values(
            value=bindparam('value')
        ).where(
            and_(
                table_graph_val.c.graph == bindparam('graph'),
                table_graph_val.c.key == bindparam('key'),
                table_graph_val.c.branch == bindparam('branch'),
                table_graph_val.c.rev == bindparam('rev')
            )
        ).compile(dialect=dialect),
        'node_val_items': select(
            [
                table_node_val.c.key,
                table_node_val.c.value
            ]
        ).select_from(
            node_val_hirev_join(
                [
                    table_node_val.c.graph == bindparam('graph'),
                    table_node_val.c.node == bindparam('node'),
                    table_node_val.c.branch == bindparam('branch'),
                    table_node_val.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'node_val_get': select(
            [
                table_node_val.c.value
            ]
        ).select_from(
            node_val_hirev_join(
                [
                    table_node_val.c.graph == bindparam('graph'),
                    table_node_val.c.node == bindparam('node'),
                    table_node_val.c.key == bindparam('key'),
                    table_node_val.c.branch == bindparam('branch'),
                    table_node_val.c.rev <= bindparam('rev')
                ]
            )
        ).where(
            table_node_val.c.value != null()
        ).compile(dialect=dialect),
        'node_val_ins': table_node_val.insert().values(
            graph=bindparam('graph'),
            node=bindparam('node'),
            key=bindparam('key'),
            branch=bindparam('branch'),
            rev=bindparam('rev'),
            value=bindparam('value')
        ).compile(dialect=dialect),
        'node_val_upd': table_node_val.update().values(
            value=bindparam('value')
        ).where(
            and_(
                table_node_val.c.graph == bindparam('graph'),
                table_node_val.c.node == bindparam('node'),
                table_node_val.c.key == bindparam('key'),
                table_node_val.c.branch == bindparam('branch'),
                table_node_val.c.rev == bindparam('rev')
            )
        ).compile(dialect=dialect),
        'edge_exists': select(
            [table_edges.c.extant]
        ).select_from(
            edges_recent_join(
                [
                    table_edges.c.graph == bindparam('graph'),
                    table_edges.c.nodeA == bindparam('nodeA'),
                    table_edges.c.nodeB == bindparam('nodeB'),
                    table_edges.c.idx == bindparam('idx'),
                    table_edges.c.branch == bindparam('branch'),
                    table_edges.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'edges_extant': select(
            [
                table_edges.c.nodeA,
                table_edges.c.extant
            ]
        ).select_from(
            edges_recent_join(
                [
                    table_edges.c.graph == bindparam('graph'),
                    table_edges.c.branch == bindparam('branch'),
                    table_edges.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'nodeAs': select(
            [
                table_edges.c.nodeA,
                table_edges.c.extant
            ]
        ).select_from(
            edges_recent_join(
                [
                    table_edges.c.graph == bindparam('graph'),
                    table_edges.c.nodeB == bindparam('dest'),
                    table_edges.c.branch == bindparam('branch'),
                    table_edges.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'nodeBs': select(
            [
                table_edges.c.nodeB,
                table_edges.c.extant
            ]
        ).select_from(
            edges_recent_join(
                [
                    table_edges.c.graph == bindparam('graph'),
                    table_edges.c.nodeA == bindparam('orig'),
                    table_edges.c.branch == bindparam('branch'),
                    table_edges.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'multi_edges': select(
            [
                table_edges.c.idx,
                table_edges.c.extant
            ]
        ).select_from(
            edges_recent_join(
                [
                    table_edges.c.graph == bindparam('graph'),
                    table_edges.c.nodeA == bindparam('orig'),
                    table_edges.c.nodeB == bindparam('dest'),
                    table_edges.c.branch == bindparam('branch'),
                    table_edges.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'edge_exist_ins': table_edges.insert().values(
            graph=bindparam('graph'),
            nodeA=bindparam('orig'),
            nodeB=bindparam('dest'),
            idx=bindparam('idx'),
            branch=bindparam('branch'),
            rev=bindparam('rev'),
            extant=bindparam('extant')
        ).compile(dialect=dialect),
        'edge_exist_upd': table_edges.update().values(
            extant=bindparam('extant')
        ).where(
            and_(
                table_edges.c.graph == bindparam('graph'),
                table_edges.c.nodeA == bindparam('orig'),
                table_edges.c.nodeB == bindparam('dest'),
                table_edges.c.idx == bindparam('idx'),
                table_edges.c.branch == bindparam('branch'),
                table_edges.c.rev == bindparam('rev')
            )
        ).compile(dialect=dialect),
        'edge_val_items': select(
            [
                table_edge_val.c.key,
                table_edge_val.c.value
            ]
        ).select_from(
            edge_val_recent_join(
                [
                    table_edge_val.c.graph == bindparam('graph'),
                    table_edge_val.c.nodeA == bindparam('orig'),
                    table_edge_val.c.nodeB == bindparam('dest'),
                    table_edge_val.c.idx == bindparam('idx'),
                    table_edge_val.c.branch == bindparam('branch'),
                    table_edge_val.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect),
        'edge_val_get': select(
            [
                table_edge_val.c.value
            ]
        ).select_from(
            edge_val_recent_join(
                [
                    table_edge_val.c.graph == bindparam('graph'),
                    table_edge_val.c.nodeA == bindparam('orig'),
                    table_edge_val.c.nodeB == bindparam('dest'),
                    table_edge_val.c.idx == bindparam('idx'),
                    table_edge_val.c.key == bindparam('key'),
                    table_edge_val.c.branch == bindparam('branch'),
                    table_edge_val.c.rev <= bindparam('rev')
                ]
            )
        ).compile(dialect=dialect)
    }

    for t in table.values():
        r['create_' + t.name] = CreateTable(t).compile(dialect=dialect)
    for (tab, idx) in index.items():
        r['index_' + tab] = CreateIndex(idx).compile(dialect=dialect)

    return r


class Alchemist(object):
    """Holds an engine and runs queries on it.

    """
    def __init__(self, engine):
        """Open a connection.

        Store a pointer to the metadata object object locally, for
        convenience.

        """
        self.engine = engine
        self.conn = self.engine.connect()
        self.meta = meta
        self.sql = compile_sql(self.engine.dialect)

    def ctbranch(self, branch):
        """Query to count the number of branches that exist."""
        return self.conn.execute(
            self.sql['ctbranch'],
            branch=branch
        )

    def ctgraph(self, graph):
        """Query to count the number of graphs that have been created."""
        return self.conn.execute(
            self.sql['ctgraph'],
            graph=graph
        )

    def allbranch(self):
        """Iterate over all available branch data."""
        return self.conn.execute(
            self.sql['allbranch']
        )

    def global_get(self, key):
        """Get the value for a global key."""
        return self.conn.execute(
            self.sql['global_get'],
            key=key
        )

    def global_items(self):
        """Iterate over key-value pairs set globally."""
        return self.conn.execute(
            self.sql['global_items']
        )

    def ctglobal(self):
        """Count keys set globally."""
        return self.conn.execute(
            self.sql['ctglobal']
        )

    def new_graph(self, graph, typ):
        """Create a graph of a given type."""
        return self.conn.execute(
            self.sql['new_graph'],
            graph=graph,
            type=typ
        )

    def graph_type(self, graph):
        """Fetch the type of the named graph."""
        return self.conn.execute(
            self.sql['graph_type'],
            graph=graph
        )

    def new_branch(self, branch, parent, parent_rev):
        """Declare that the branch ``branch`` is a child of ``parent``
        starting at revision ``parent_rev``.

        """
        return self.conn.execute(
            self.sql['new_branch'],
            branch=branch,
            parent=parent,
            parent_rev=parent_rev
        )

    def del_edge_val_graph(self, graph):
        """Delete all edge attributes from ``graph``."""
        return self.conn.execute(
            self.sql['del_edge_val_graph'],
            graph=graph
        )

    def del_node_val_graph(self, graph):
        """Delete all node attributes from ``graph``."""
        return self.conn.execute(
            self.sql['del_node_val_graph'],
            graph=graph
        )

    def del_node_graph(self, graph):
        """Delete all nodes from ``graph``."""
        return self.conn.execute(
            self.sql['del_node_graph'],
            graph=graph
        )

    def del_graph(self, graph):
        """Delete the graph header."""
        return self.conn.execute(
            self.sql['del_graph'],
            graph=graph
        )

    def parrev(self, branch):
        """Fetch the revision at which ``branch`` forks off from its
        parent.

        """
        return self.conn.execute(
            self.sql['parrev'],
            branch=branch
        )

    def parparrev(self, branch):
        """Fetch the name of ``branch``'s parent, and the revision at which
        they part.

        """
        return self.conn.execute(
            self.sql['parparrev'],
            branch=branch
        )

    def global_ins(self, key, value):
        """Insert a record into the globals table indicating that
        ``key=value``.

        """
        return self.conn.execute(
            self.sql['global_ins'],
            key=key,
            value=value
        )

    def global_upd(self, key, value):
        """Update the existing global record for ``key`` so that it is set to
        ``value``.

        """
        return self.conn.execute(
            self.sql['global_upd'],
            key=key,
            value=value
        )

    def global_del(self, key):
        """Delete the record for global variable ``key``."""
        return self.conn.execute(
            self.sql['global_del'],
            key=key
        )

    def nodes_extant(self, graph, branch, rev):
        """Query for nodes that exist in ``graph`` at ``(branch, rev)``."""
        return self.conn.execute(
            self.sql['nodes_extant'],
            graph=graph,
            branch=branch,
            rev=rev
        )

    def node_exists(self, graph, node, branch, rev):
        """Query for whether or not ``node`` exists in ``graph`` at ``(branch,
        rev)``.

        """
        return self.conn.execute(
            self.sql['node_exists'],
            graph=graph,
            node=node,
            branch=branch,
            rev=rev
        )

    def exist_node_ins(self, graph, node, branch, rev, extant):
        """Insert a record to indicate whether or not ``node`` exists in
        ``graph`` at ``(branch, rev)``.

        """
        return self.conn.execute(
            self.sql['exist_node_ins'],
            graph=graph,
            node=node,
            branch=branch,
            rev=rev,
            extant=extant
        )

    def exist_node_upd(self, extant, graph, node, branch, rev):
        """Update the record previously inserted by ``exist_node_ins``,
        indicating whether ``node`` exists in ``graph`` at ``(branch,
        rev)``.

        """
        return self.conn.execute(
            self.sql['exist_node_upd'],
            extant=extant,
            graph=graph,
            node=node,
            branch=branch,
            rev=rev
        )

    def graph_val_items(self, graph, branch, rev):
        """Query the most recent keys and values for the attributes of
        ``graph`` at ``(branch, rev)``.

        """
        return self.conn.execute(
            self.sql['graph_val_items'],
            graph=graph,
            branch=branch,
            rev=rev
        )

    def graph_val_get(self, graph, key, branch, rev):
        """Query the most recent value for ``graph``'s ``key`` as of
        ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['graph_val_get'],
            graph=graph,
            key=key,
            branch=branch,
            rev=rev,
        )

    def graph_val_ins(self, graph, key, branch, rev, value):
        """Insert a record to indicate that ``key=value`` on ``graph`` as of
        ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['graph_val_ins'],
            graph=graph,
            key=key,
            branch=branch,
            rev=rev,
            value=value
        )

    def graph_val_upd(self, value, graph, key, branch, rev):
        """Update the record previously inserted by ``graph_val_ins``"""
        return self.conn.execute(
            self.sql['graph_val_upd'],
            value=value,
            graph=graph,
            key=key,
            branch=branch,
            rev=rev
        )

    def node_val_items(self, graph, node, branch, rev):
        """Get all the most recent values of all the keys on ``node`` in
        ``graph`` as of ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['node_val_items'],
            graph=graph,
            node=node,
            branch=branch,
            rev=rev
        )

    def node_val_get(self, graph, node, key, branch, rev):
        """Get the most recent value for ``key`` on ``node`` in ``graph`` as
        of ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['node_val_get'],
            graph=graph,
            node=node,
            key=key,
            branch=branch,
            rev=rev
        )

    def node_val_ins(self, graph, node, key, branch, rev, value):
        """Insert a record to indicate that the value of ``key`` on ``node``
        in ``graph`` as of ``(branch, rev)`` is ``value``.

        """
        return self.conn.execute(
            self.sql['node_val_ins'],
            graph=graph,
            node=node,
            key=key,
            branch=branch,
            rev=rev,
            value=value
        )

    def node_val_upd(self, value, graph, node, key, branch, rev):
        """Update the record previously inserted by ``node_val_ins``"""
        return self.conn.execute(
            self.sql['node_val_upd'],
            value=value,
            graph=graph,
            node=node,
            key=key,
            branch=branch,
            rev=rev
        )

    def edge_exists(self, graph, nodeA, nodeB, idx, branch, rev):
        """Query for whether a particular edge exists at a particular
        ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['edge_exists'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            branch=branch,
            rev=rev
        )

    def edges_extant(self, graph, branch, rev):
        """Query for all edges that exist in ``graph`` as of ``(branch,
        rev)``

        """
        return self.conn.execute(
            self.sql['edges_extant'],
            graph=graph,
            branch=branch,
            rev=rev
        )

    def nodeAs(self, graph, nodeB, branch, rev):
        """Query for edges that end at ``nodeB`` in ``graph`` as of ``(branch,
        rev)``

        """
        return self.conn.execute(
            self.sql['nodeAs'],
            graph=graph,
            dest=nodeB,
            branch=branch,
            rev=rev
        )

    def nodeBs(self, graph, nodeA, branch, rev):
        """Query for the nodes at which edges that originate from ``nodeA``
        end.

        """
        return self.conn.execute(
            self.sql['nodeBs'],
            graph=graph,
            orig=nodeA,
            branch=branch,
            rev=rev
        )

    def multi_edges(self, graph, nodeA, nodeB, branch, rev):
        """Query for all edges from ``nodeA`` to ``nodeB``. Only makes sense
        if we're dealing with a :class:`MultiGraph` or
        :class:`MultiDiGraph`.

        """
        return self.conn.execute(
            self.sql['multi_edges'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            branch=branch,
            rev=rev
        )

    def edge_exist_ins(self, graph, nodeA, nodeB, idx, branch, rev, extant):
        """Indicate that there is (or isn't) an edge from ``nodeA`` to
        ``nodeB`` in ``graph`` as of ``(branch, rev)``.

        ``idx`` should be ``0`` unless ``graph`` is a
        :class:`MultiGraph` or :class:`MultiDiGraph`.

        """
        return self.conn.execute(
            self.sql['edge_exist_ins'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            branch=branch,
            rev=rev,
            extant=extant
        )

    def edge_exist_upd(self, extant, graph, nodeA, nodeB, idx, branch, rev):
        """Update a record previously inserted with ``edge_exist_ins``."""
        return self.conn.execute(
            self.sql['edge_exist_upd'],
            extant=extant,
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            branch=branch,
            rev=rev
        )

    def edge_val_items(self, graph, nodeA, nodeB, idx, branch, rev):
        """Iterate over key-value pairs that are set on an edge as of
        ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['edge_val_items'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            branch=branch,
            rev=rev
        )

    def edge_val_get(self, graph, nodeA, nodeB, idx, key, branch, rev):
        """Get the value of a key on an edge that is relevant as of ``(branch,
        rev)``

        """
        return self.conn.execute(
            self.sql['edge_val_get'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            key=key,
            branch=branch,
            rev=rev
        )

    def edge_val_ins(self, graph, nodeA, nodeB, idx, key, branch, rev, value):
        """Insert a record to indicate the value of a key on an edge as of
        ``(branch, rev)``

        """
        return self.conn.execute(
            self.sql['edge_val_ins'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            key=key,
            branch=branch,
            rev=rev,
            value=value
        )

    def edge_val_upd(self, value, graph, nodeA, nodeB, idx, key, branch, rev):
        """Update a record previously inserted by ``edge_val_ins``"""
        return self.conn.execute(
            self.sql['edge_val_upd'],
            graph=graph,
            orig=nodeA,
            dest=nodeB,
            idx=idx,
            key=key,
            branch=branch,
            rev=rev
        )


if __name__ == '__main__':
    e = create_engine('sqlite:///:memory:')
    out = dict(
        (k, str(v)) for (k, v) in
        compile_sql(e.dialect).items()
    )

    print(dumps(out))
