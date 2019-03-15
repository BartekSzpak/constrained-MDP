import collections
import pickle

import matplotlib
import pylab
from matplotlib.ticker import FormatStrFormatter
from numpy import mean

from util import standardErr

rndSeeds = 1000

width = height = 5

lensOfQ = {}
lensOfQRelPhi = {}
times = {}

#proportionRange = [0.01] + [0.1 * proportionInt for proportionInt in range(10)] + [0.99]
carpetNums = [8, 9, 10, 11, 12]

# will check what methods are run from data
includeOpt = True
includeRandom = False

methods = (['opt'] if includeOpt else []) \
          + ['iisAndRelpi', 'iisOnly', 'relpiOnly', 'maxProb', 'piHeu'] \
          + (['random'] if includeRandom else [])

markers = {'opt': 'r*-', 'iisAndRelpi': 'bo-', 'iisOnly': 'bs--', 'relpiOnly': 'bd-.', 'maxProb': 'g^-', 'piHeu': 'm+-', 'random': 'c.-'}
names = {'opt': 'Optimal', 'iisAndRelpi': 'SetCover', 'iisOnly': 'SetCover (IIS)', 'relpiOnly': 'SetCover (rel. feat.)', 'maxProb': 'Greed. Prob.',\
         'piHeu': 'Most-Likely', 'random': 'Descending'}

# output the difference of two vectors
vectorDiff = lambda v1, v2: map(lambda e1, e2: e1 - e2, v1, v2)
# output the ratio of two vectors. 1 if e2 == 0
vectorRatio = lambda v1, v2: map(lambda e1, e2: e1 / e2 if e2 != 0 else 1, v1, v2)

# for output as latex table
outputFormat = lambda d: '$' + str(round(mean(d), 4)) + ' \pm ' + str(round(standardErr(d), 4)) + '$'

def plot(x, y, methods, xlabel, ylabel, filename):
  """
  plot data.

  :param x: x axis
  :param y: y(method, x_elem) is a vector that contains raw data
  :param methods: methods to plot, each has a legend
  :param xlabel: name of xlabel
  :param ylabel: name of ylabel
  :param filename: output to filename.pdf
  :return:
  """
  yMean = lambda method: [mean(y(method, xElem)) for xElem in x]
  yCI = lambda method: [standardErr(y(method, xElem)) for xElem in x]

  fig = pylab.figure()

  ax = pylab.gca()
  for method in methods:
    print method, yMean(method), yCI(method)
    ax.errorbar(x, yMean(method), yCI(method), fmt=markers[method], mfc='none', label=names[method], markersize=10, capsize=5)

  pylab.xlabel(xlabel)
  pylab.ylabel(ylabel)
  pylab.legend()
  ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))

  fig.savefig(filename + ".pdf", dpi=300, format="pdf")

  pylab.close()

def scatter(x, y, xlabel, ylabel, filename):
  fig = pylab.figure()

  for method in methods:
    # weirdly scatter doesn't have a fmt parameter. setting marker and color separately
    pylab.scatter(x, y(method), c=markers[method][0], marker=markers[method][1])

  ax = pylab.gca()
  pylab.xlabel(xlabel)
  pylab.ylabel(ylabel)
  pylab.legend()
  ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))

  fig.savefig(filename + ".pdf", dpi=300, format="pdf")

  pylab.close()

def plotNumVsProportion(pfRange, pfStep):
  """
  Plot the the number of queried features vs the proportion of free features
  """
  # fixed carpet num for this exp
  carpets = 10

  for method in methods:
    for pf in pfRange:
      lensOfQ[method, pf] = []
      times[method, pf] = []

  validInstances = []

  for rnd in range(rndSeeds):
    # set to true if this instance is valid (no safe init policy)
    rndProcessed = False

    for pf in pfRange:
      try:
        pfUb = pf + pfStep

        filename = str(width) + '_' + str(height) + '_' + str(carpets) + '_' + str(pf) + '_' + str(pfUb) + '_' + str(rnd) + '.pkl'
        data = pickle.load(open(filename, 'rb'))
      except IOError:
        print filename, 'not exist'
        continue

      # number of features queried
      for method in methods:
        lensOfQ[method, pf].append(len(data['q'][method]))
        times[method, pf].append(data['t'][method])
      
      if not rndProcessed:
        rndProcessed = True

        validInstances.append(rnd)
    
  print 'valid instances', len(validInstances)
  assert len(validInstances) > 0

  # show cases where method1 and method2 are different with proportion. for further debugging methods
  diffInstances = lambda pf, method1, method2:\
                  (pf, method1, method2,\
                  filter(lambda _: _[1] != _[2], zip(validInstances, lensOfQ[method1, pf], lensOfQ[method2, pf])))

  """
  for pf in pfRange: 
    print diffInstances(pf, 'iisAndRelpi', 'iisOnly')
  """

  # plot figure
  x = pfRange
  y = lambda method, pfRange: vectorDiff(lensOfQ[method, pf], lensOfQ[methods[0], pf])

  plot(x, y, methods, '$p_f$', '# of Queried Features (' + names[methods[0]] + ' as baseline)', 'lensOfQPf' + str(int(pfStep * 10)))


def plotNumVsCarpets():
  """
  plot the num of queried features / computation time vs. num of carpets
  """
  for method in methods:
    for carpetNum in carpetNums:
      lensOfQ[method, carpetNum] = []
      times[method, carpetNum] = []

    for carpetNum in range(max(carpetNums) + 1):
      # relevant features is going to be at most the number of unknown features anyway
      lensOfQRelPhi[method, carpetNum] = []

  iiss = {}
  domPis = {}

  # a trial is valid (and its data should be counted) when no initial safe policy exists
  validInstances = {}
  # trials where the robot is able to find a safe policy after querying
  # (instead of claiming that ho safe policies exist)
  solvableIns = {}

  # initialize dictionaries
  for carpetNum in carpetNums:
    iiss[carpetNum] = []
    domPis[carpetNum] = []
    solvableIns[carpetNum] = []
    validInstances[carpetNum] = []

  for rnd in range(rndSeeds):
    for carpetNum in carpetNums:
      try:
        filename = str(width) + '_' + str(height) + '_' + str(carpetNum) + '_0_1_' +  str(rnd) + '.pkl'
        data = pickle.load(open(filename, 'rb'))
      except IOError:
        print filename, 'not exist'
        continue

      # see which features appear in relevant features of any dominating policy
      relFeats = len(filter(lambda _: any(_ in relFeats for relFeats in data['relFeats']), range(carpetNum)))
      # get stats
      for method in methods:
        lensOfQ[method, carpetNum].append(len(data['q'][method]))
        lensOfQRelPhi[method, relFeats].append(len(data['q'][method]))
        times[method, carpetNum].append(data['t'][method])

      iiss[carpetNum].append(len(data['iiss']))
      domPis[carpetNum].append(len(data['relFeats']))
      # num of relevant features

      validInstances[carpetNum].append(rnd)
      if data['solvable']: solvableIns[carpetNum].append(rnd)

      # print the case where ouralg is suboptimal for analysis
      if 'opt' in methods and len(data['q']['opt']) < len(data['q']['iisAndRelpi']):
        print 'rnd', rnd, 'carpetNum', carpetNum, 'opt', data['q']['opt'], 'iisAndRelpi', data['q']['iisAndRelpi']

  #print 'iiss', [round(mean(iiss[carpetNum]), 2) for carpetNum in carpetNums]
  #print 'relFeats', [round(mean(domPis[carpetNum]), 2) for carpetNum in carpetNums]

  print 'valid instances', [len(validInstances[carpetNum]) for carpetNum in carpetNums]
  print 'solvable instances ratio', [round(1.0 * len(solvableIns[carpetNum]) / len(validInstances[carpetNum]), 2) for carpetNum in carpetNums]

  print '# of queries'
  x = carpetNums
  # use the first method as baseline, a bit hacky here.
  #y = lambda method, carpetNum: vectorDiff(lensOfQ[method, carpetNum], lensOfQ[methods[0], carpetNum])
  y = lambda method, carpetNum: vectorRatio(lensOfQ[method, carpetNum], lensOfQ[methods[0], carpetNum])
  plot(x, y, methods, '# of Carpets', '# of Queried Features (' + names[methods[0]] + ' as baseline)', 'lensOfQCarpets')

  print 'compute time'
  x = carpetNums
  y = lambda method, carpetNum: times[method, carpetNum]
  plot(x, y, methods, '# of Carpets', 'Computation Time (sec.)', 'timesCarpets')

  # plot num of features queried based on the num of dom pis
  x = range(max(carpetNums))
  y = lambda method, relFeat: vectorDiff(lensOfQRelPhi[method, relFeat], lensOfQRelPhi[methods[0], relFeat])
  plot(x, y, methods, "# of Relevant Features", "# of Queried Features (" + names[methods[0]] + " as baseline)", 'lensOfQCarpets_relphis')


font = {'size': 13}
matplotlib.rc('font', **font)

pfCandidates = [(0.2, [0, 0.2, 0.4, 0.6, 0.8]),\
#                (0.3, [0, 0.35, 0.7]),\
                (0.5, [0, 0.25, 0.5])]

# exp 1: varying num of carpets
plotNumVsCarpets()

# exp 2: varying pfs
#for (pfStep, pfRange) in pfCandidates: plotNumVsProportion(pfRange, pfStep)