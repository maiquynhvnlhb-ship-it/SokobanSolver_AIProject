
from importlib import import_module

_ALGOS = {
    "BFS": "algorithms.bfs",
    "DFS": "algorithms.dfs",
    "Greedy": "algorithms.greedy",
    "A*": "algorithms.astar",
    "Beam": "algorithms.BeamSearch",
    "SA": "algorithms.SimulatedAnnealing",
    "And_Or": "algorithms.and_or",
    "PO": "algorithms.PartialObservable",
    "Back": "algorithms.Backtracking",
    "Forward": "algorithms.ForwardChecking",
}

def get_names():
    return list(_ALGOS.keys())

def get(name: str):
    modname = _ALGOS[name]
    return import_module(modname)
