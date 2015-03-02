# -*- coding: utf-8 -*-

import copy

from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
def topological_sort(node_list):
    all_nodes  = _get_nodes_dictionary(node_list)
    if all_nodes is None:
        return None

    nodes_to_sort       = all_nodes.copy()
    sorted_nodes_names  = []

    while len(nodes_to_sort) > 0:
        (node_name, node) = nodes_to_sort.popitem()
        if not _recursive_topological_sort(node,
                                           all_nodes,
                                           nodes_to_sort,
                                           [],
                                           sorted_nodes_names):
            return None

    return _get_node_list(sorted_nodes_names, all_nodes)

#-------------------------------------------------------------------------------
def topological_sort_node(node, node_list):
    all_nodes  = _get_nodes_dictionary(node_list)
    if all_nodes is None:
        return None

    nodes_to_sort = all_nodes.copy()
    sorted_nodes_names = []

    if not _recursive_topological_sort(node,
                                       all_nodes,
                                       nodes_to_sort,
                                       [],
                                       sorted_nodes_names):
        return None

    return _get_node_list(sorted_nodes_names, all_nodes)

#-------------------------------------------------------------------------------
def _get_nodes_dictionary(node_list):
    node_dictionary = {}
    for node_it in node_list:
        node_name = node_it.name()
        if node_name in node_dictionary:
            log_error("Found two nodes named \"{0}\" : {1} and {2}",
                      node_name,
                      all_nodes[node_name].__class__.__name__,
                      node_it.__class__.__name__)
            return None
        node_dictionary[node_it.name()] = node_it
    return node_dictionary

#-------------------------------------------------------------------------------
def _get_node_list(node_name_list, node_dictionary):
    result = []
    for node_name_it in node_name_list:
        node_it = node_dictionary[node_name_it]
        result.append(node_it)
    return result

#-------------------------------------------------------------------------------
def _recursive_topological_sort(node,
                                all_nodes,
                                nodes_to_sort,
                                visited_nodes_names,
                                sorted_nodes_names):
    node_name = node.name()

    if node_name in visited_nodes_names:
        return False

    if node_name not in sorted_nodes_names:
        visited_nodes_names.append(node_name)

        for dependency_name_it in node.dependencies():
            if dependency_name_it not in all_nodes:
                log_warning("Uknown node \"{0}\" in \"{1}\" dependencies", dependency_name_it, node_name)
                continue

            dependency_it = all_nodes[dependency_name_it]
            no_circular_dependency = _recursive_topological_sort(dependency_it,
                                                                 all_nodes,
                                                                 nodes_to_sort,
                                                                 visited_nodes_names,
                                                                 sorted_nodes_names)
            if(not no_circular_dependency):
                log_error("Circular node dependency detected : {0} -> {1}",
                          node_name,
                          dependency_name_it)
                return False

        visited_nodes_names.remove(node_name)
        sorted_nodes_names.append(node_name)
    return True
