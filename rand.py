import math

class Random:

	def __init__(self, seed):
		self.IA = 16807		 # constant used for RNG
							 # (see p37 of Simulation by Ross)
		self.IM = 2147483647 # constant used for RNG (2^31-1)
		self.seed = seed	 # state of the RNG
		self.initseed = seed

	def reset(self):
		self.seed = self.initseed

	def ran0(self):
		'''Returns a random integer in [1,$IM-1]; changes self.seed, ie, RNG
		state.	(This is ran0 from Numerical Recipes and has a period
		of ~2 billion.)

		'''
		self.seed = self.IA * self.seed % self.IM
		return self.seed

	def ran01(self):
		'''Returns a U(0,1) random number.'''
		return self.ran0() / self.IM

	def ranx(self, x):
		'''Move the PRNG state forward x times and return the result'''
		result = None
		for i in range(x):
			result = self.ran01()
		return result or (self.seed / self.IM)

class ExpRand(Random):

	def __init__(self, seed, gap):
		super().__init__(seed)
		self.gap = gap

	def exprand(self):
		'''Returns a random number drawn from an exponential distribution with mean
		self.gap.

		'''
		return -1 * self.gap * math.log(self.ran01())

	def nextping(self, prev):
		'''Takes previous ping time, returns random next ping time (unixtime).
		NB: this has the side effect of changing the RNG state ($seed)
			and so should only be called once per next ping to calculate,
			after calling prevping.
		'''
		# XXX round1
		return max(prev + 1, round(prev + self.exprand()))

	def prevping(self, t):
		'''Computes the last scheduled ping time before time t.'''
		self.seed = self.initseed
		# Starting at the beginning of time, walk forward computing
		# next pings until the next ping is >= t.
		nxtping = 1184083200  # the birth of timepie/tagtime!
		# import time
		# nxtping = time.time() - 1000 # XXX debugging
		lstping = nxtping
		lstseed = self.seed
		while nxtping < t:
			lstping = nxtping
			lstseed = self.seed # XXX this is an ugly way to handle state
			nxtping = self.nextping(nxtping)
		self.seed = lstseed
		return lstping
