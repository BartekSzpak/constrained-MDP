import copy
from operator import mul

import numpy
from numpy import random

from algorithms.consQueryAgents import ConsQueryAgent
from algorithms.initialSafeAgent import GreedyForSafetyAgent
from algorithms.rewardQueryAgents import GreedyConstructRewardAgent
from util import normalize


class JointUncertaintyQueryAgent(ConsQueryAgent):
  """
  Querying under reward uncertainty and safety-constraint uncertainty
  """
  def __init__(self, mdp, consStates, goalStates, consProbs, costOfQuery):
    ConsQueryAgent.__init__(self, mdp, consStates, goalStates=goalStates, consProbs=consProbs)

    self.costOfQuery = costOfQuery

  def updateFeats(self, newFreeCon=None, newLockedCon=None):
    # share some code as InitialSafeAgent, but I don't want to make this class a subclass of that
    if newFreeCon is not None:
      self.unknownCons.remove(newFreeCon)
      self.knownFreeCons.append(newFreeCon)
    if newLockedCon is not None:
      self.unknownCons.remove(newLockedCon)
      self.knownLockedCons.append(newLockedCon)

  def updateReward(self, possibleTrueRewardIndices):
    self.mdp.psi = self.updateARewardDistribution(possibleTrueRewardIndices, self.mdp.psi)

  def updateARewardDistribution(self, possibleTrueRewardIndices, psi):
    for rIdx in range(len(psi)):
      if rIdx not in possibleTrueRewardIndices:
        psi[rIdx] = 0
    return normalize(psi)

  def computeConsistentRewardIndices(self):
    return filter(lambda rIdx: self.mdp.psi[rIdx] > 0, range(len(self.mdp.psi)))

  def computeCurrentSafelyOptPiValue(self):
    return self.findConstrainedOptPi(activeCons=self.unknownCons)['obj']


class JointUncertaintyOptimalQueryAgent(JointUncertaintyQueryAgent):
  def computeOptimalQueries(self):
    """
    find the optimal query policy by evaluating all possible query policies
    """
    pass

  def findQuery(self):
    pass


class JointUncertaintyQueryByMyopicSelectionAgent(JointUncertaintyQueryAgent):
  """
  Planning several steps into the future
  """
  def __init__(self, mdp, consStates, goalStates=(), consProbs=None, costOfQuery=0):
    JointUncertaintyQueryAgent.__init__(self, mdp, consStates, goalStates=goalStates, consProbs=consProbs, costOfQuery=costOfQuery)

    # create two query agents specialized on reward / feature queries
    self.rewardQueryAgent = GreedyConstructRewardAgent(mdp, 2)
    self.featureQueryAgent = GreedyForSafetyAgent(mdp, consStates, goalStates, consProbs, improveSafePis=True)

  def updateFeats(self, newFreeCon=None, newLockedCon=None):
    JointUncertaintyQueryAgent.updateFeats(self, newFreeCon, newLockedCon)

    # need to update the set cover structure
    self.featureQueryAgent.updateFeats(newFreeCon, newLockedCon)
    self.featureQueryAgent.computePolicyRelFeats()
    self.featureQueryAgent.computeIISs()

  def findRewardQuery(self):
    """
    encode consStates and pf into the transition function,
    then use greedy construction and projection to find close-to-optimal reward query
    """
    psiSupports = filter(lambda _: _ > 0, self.mdp.psi)
    # psi cannot have 0 support
    assert len(psiSupports) > 0
    # if the true reward function is known, no need to pose more reward queries
    if len(psiSupports) == 1: return None

    self.rewardQueryAgent.mdp.updatePsi(self.mdp.psi)
    self.rewardQueryAgent.mdp.encodeConstraintIntoTransition([self.consStates[_] for _ in self.knownLockedCons + self.unknownCons])

    return self.rewardQueryAgent.findBinaryResponseRewardSetQuery()

  def findFeatureQuery(self):
    """
    use set-cover based algorithm and use the mean reward function (mdp.r does that)
    #fixme assume safe policies exist for now

    when safe policies exist, need to modify the original algorithm:
    computing the set structures by first removing safe dominating policies (set includeSafePolicies to True),
    that is, we want to minimize the number of queries to find *additional* dominating policies.
    """
    # after computing rel feats, check if it's empty. if so, nothing need to be queried.
    #if len(self.featureQueryAgent.relFeats) == 0: return None
    if len(self.featureQueryAgent.domPiFeats) == 0 or len(self.featureQueryAgent.iiss) == 0: return None

    return self.featureQueryAgent.findQuery()

  def computeEVOI(self, query):
    (qType, qContent) = query
    # if the query gives up, then epu is 0
    if qContent is None: return 0

    priorValue = self.computeCurrentSafelyOptPiValue()

    if qType == 'F':
      feat = qContent
      epu = self.consProbs[feat] * self.findConstrainedOptPi(activeCons=set(self.unknownCons) - {feat,})['obj']\
          + (1 - self.consProbs[feat]) * self.findConstrainedOptPi(activeCons=self.unknownCons)['obj']
    elif qType == 'R':
      rIndices = qContent

      mdpIfTrueReward = copy.deepcopy(self.mdp)
      mdpIfTrueReward.updatePsi(self.updateARewardDistribution(rIndices, psi=mdpIfTrueReward.psi))
      posteriorValueIfTrue = self.findConstrainedOptPi(activeCons=self.unknownCons, mdp=mdpIfTrueReward)['obj']

      mdpIfFalseReward = copy.deepcopy(self.mdp)
      mdpIfFalseReward.updatePsi(self.updateARewardDistribution(set(range(len(self.mdp.psi))) - set(rIndices),
                                                            psi=mdpIfFalseReward.psi))
      posteriorValueIfFalse = self.findConstrainedOptPi(activeCons=self.unknownCons, mdp=mdpIfFalseReward)['obj']

      epu = sum(self.mdp.psi[_] for _ in rIndices) * posteriorValueIfTrue +\
          + (1 - sum(self.mdp.psi[_] for _ in rIndices)) * posteriorValueIfFalse
    else:
      raise Exception('unknown query ' + query)

    evoi = epu - priorValue
    assert evoi >= 0
    return evoi

  def findQuery(self):
    """
    compute the myopically optimal reward query vs feature query, pose the on that has larger EPU value
    """
    rewardQuery = ('R', self.findRewardQuery())
    featureQuery = ('F', self.findFeatureQuery())

    rewardQEVOI = self.computeEVOI(rewardQuery)
    featureQEVOI = self.computeEVOI(featureQuery)

    print 'EVOI', rewardQuery, rewardQEVOI
    print 'EVOI', featureQuery, featureQEVOI

    if rewardQEVOI < self.costOfQuery and featureQEVOI < self.costOfQuery:
      # stop querying
      return None
    elif rewardQEVOI > featureQEVOI:
      return rewardQuery
    else:
      return featureQuery


class JointUncertaintyQueryBySamplingDomPisAgent(JointUncertaintyQueryAgent):
  """
  Sample a set of dominating policies according to their probabilities of being free and their values.
  Then query the features that would make them safely-optimal.
  """
  def __init__(self, mdp, consStates, goalStates=(), consProbs=None, costOfQuery=1):
    JointUncertaintyQueryAgent.__init__(self, mdp, consStates, goalStates=goalStates, consProbs=consProbs,
                                        costOfQuery=costOfQuery)

    # initialize objectDomPi to be None, will be computed in findQuery
    self.objectDomPi = None

  class DomPiData:
    """
    For a dominating policy, we want to keep its weighted value
    (prob that it is safe, prob that the reward it optimizes is the true reward, and the value of the policy),
    the rewards it optimizes, and the constraints that it violates
    """
    def __init__(self):
      self.weightedValue = 0
      self.optimizedRewards = []
      self.violatedCons = None

  def sampleDomPi(self):
    """
    (re)compute all dominating policies given reward and safety uncertainty
    and then sample one
    stored in self.dompis = [(dompi, weighted_prob)]
    """
    domPisData = {}

    for rIdx in range(len(self.mdp.rFuncs)):
      r = self.mdp.rFuncs[rIdx]
      rProb = self.mdp.psi[rIdx]

      rewardCertainMDP = copy.deepcopy(self.mdp)
      rewardCertainMDP.setReward(r)

      rewardCertainConsAgent = ConsQueryAgent(rewardCertainMDP, self.consStates, self.goalCons, self.consProbs,
                                              knownFreeCons=self.knownFreeCons, knownLockedCons=self.knownLockedCons)
      _, domPis = rewardCertainConsAgent.findRelevantFeaturesAndDomPis()

      for domPi in domPis:
        piValue = rewardCertainConsAgent.computeValue(domPi)
        relFeats = rewardCertainConsAgent.findViolatedConstraints(domPi)
        safeProb = reduce(mul, [self.consProbs[feat] for feat in relFeats], 1)

        domPiHashable = frozenset(domPi.items())
        if domPiHashable not in domPisData.keys():
          domPisData[domPiHashable] = self.DomPiData()
          domPisData[domPiHashable].violatedCons = relFeats

        domPisData[domPiHashable].weightedValue += safeProb * rProb * piValue
        domPisData[domPiHashable].optimizedRewards.append(rIdx)

    # normalize values
    sumOfAllValues = sum([data.weightedValue for data in domPisData.values()])
    for domPiHashable in domPisData.keys():
      domPisData[domPiHashable].weightedValue /= sumOfAllValues

    self.objectDomPi = numpy.random.choice(domPisData.keys(), p=[data.weightedValue for data in domPisData.values()])
    self.objectDomPiData = copy.copy(domPisData[self.objectDomPi]) # hopefully python will then free domPisData

  def objectDomPiIsConsistent(self):
    """
    If the reward functions the current objectDomPi optimize are ruled out, or the current objectDomPi is knwon to be unsafe,
    then re-compute the set of dominating policies
    """
    # if the response is inconsistent with self.objectDomPi,
    # we void the current object dom pi, findQuery will recompute the object dom pi
    consistentRewardIndices = self.computeConsistentRewardIndices()
    #print 'known locked cons', self.knownLockedCons
    #print 'consistent reward indices', consistentRewardIndices
    return len(set(self.knownLockedCons).intersection(self.objectDomPiData.violatedCons)) == 0 \
      and len(set(consistentRewardIndices).intersection(self.objectDomPiData.optimizedRewards)) > 0

  def findQuery(self):
    """
    sample some dominating policies, find the most useful query?
    :return: (query type, query)
    """
    # sample dom pis, find what can make them be the safely optimal one
    if self.objectDomPi is None or not self.objectDomPiIsConsistent():
      self.sampleDomPi()

    relFeats = self.objectDomPiData.violatedCons
    unknownRelFeats = set(relFeats).intersection(self.unknownCons)
    # fixme better ways to choose queries and decide when to stop?
    if len(unknownRelFeats) > 0:
      # pose constraint queries if any relevant features are unknown
      return ('F', random.choice(list(unknownRelFeats)))
    else:
      # pose reward queries aiming to show that the rewards it optimizes is correct
      consistentRewardIndices = self.computeConsistentRewardIndices()
      assert len(consistentRewardIndices) > 0
      # no reward queries needed if no reward uncertainty
      if len(consistentRewardIndices) == 1: return None
      qReward = set(self.objectDomPiData.optimizedRewards).intersection(consistentRewardIndices)
      return ('R', list(qReward))