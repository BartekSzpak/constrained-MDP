VERBOSE = True
DEBUG = False

OPT_METHOD = 'gurobi'
#OPT_METHOD = 'cplex'

earlyStop = None
#earlyStop = 3

costOfQuery = 0.1

# experiment configuration
trialsStart = 0
trialsEnd = 1000

methods = ['myopic', 'alternate']
#methods = ['alternate']
