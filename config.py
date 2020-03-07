VERBOSE = False
DEBUG = False

OPT_METHOD = 'gurobi'
#OPT_METHOD = 'cplex'

# make this smaller because we need to find dom pis for 2^|\R| times in joint uncertainty works
earlyStop = 1

# for each domain configuration, sample the true reward function and the true free features
sampleInstances = 30

# experiment configuration
trialsStart = 0
trialsEnd = 500

methods = ['myopic', 'batch', 'dompi']

size = 6
walls = 5
numsOfCarpets = [10, 12, 14]
numsOfSwitches = [2, 4]
costsOfQuery = [0.1]
