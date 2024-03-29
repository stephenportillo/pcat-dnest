# Copyright (c) 2009, 2010, 2011, 2012 Brendon J. Brewer.
#
# This file is part of DNest3.
#
# DNest3 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DNest3 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DNest3. If not, see <http://www.gnu.org/licenses/>.

import copy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family="serif", size=12)
matplotlib.rc("text", usetex=True)

def logsumexp(values):
	biggest = np.max(values)
	x = values - biggest
	result = np.log(np.sum(np.exp(x))) + biggest
	return result

def logdiffexp(x1, x2):
	biggest = x1
	xx1 = x1 - biggest
	xx2 = x2 - biggest
	result = np.log(np.exp(xx1) - np.exp(xx2)) + biggest
	return result

def postprocess(filename, temperature=1., numResampleLogX=1, plot=True, loaded=[], \
			cut=0., save=True, zoom_in=True):
	if len(loaded) == 0:
		levels = np.atleast_2d(np.loadtxt("run-"+filename+"/levels.txt"))
		sample_info = np.atleast_2d(np.loadtxt("run-"+filename+"/sample_info.txt"))
		sample = np.atleast_2d(np.loadtxt("run-"+filename+"/sample.txt"))
		#if(sample.shape[0] == 1):
		#	sample = sample.T
	else:
		levels, sample_info, sample = loaded[0], loaded[1], loaded[2]

	sample = sample[int(cut*sample.shape[0]):, :]
	sample_info = sample_info[int(cut*sample_info.shape[0]):, :]

	if sample.shape[0] != sample_info.shape[0]:
		print('# Size mismatch. Truncating...')
		lowest = np.min([sample.shape[0], sample_info.shape[0]])
		sample = sample[0:lowest, :]
		sample_info = sample_info[0:lowest, :]

	if plot:
		if numResampleLogX > 1:
			plt.ion()

		plt.figure(1)
		plt.plot(sample_info[:,0])
		plt.xlabel("Iteration")
		plt.ylabel("Level")
		if numResampleLogX > 1:
			plt.draw()

		plt.figure(2)
		plt.subplot(2,1,1)
		plt.plot(np.diff(levels[:,0]))
		plt.ylabel("Compression")
		plt.xlabel("Level")
		xlim = plt.gca().get_xlim()
		plt.axhline(-1., color='r')
		plt.ylim(ymax=0.05)
		if numResampleLogX > 1:
			plt.draw()

		plt.subplot(2,1,2)
		good = np.nonzero(levels[:,4] > 0)[0]
		plt.plot(levels[good,3]/levels[good,4])
		plt.xlim(xlim)
		plt.ylim([0., 1.])
		plt.xlabel("Level")
		plt.ylabel("MH Acceptance")
		if numResampleLogX > 1:
			plt.draw()

	# Convert to lists of tuples
	logl_levels = [(levels[i,1], levels[i, 2]) for i in xrange(0, levels.shape[0])] # logl, tiebreaker
	logl_samples = [(sample_info[i, 1], sample_info[i, 2], i) for i in xrange(0, sample.shape[0])] # logl, tiebreaker, id
	logx_samples = np.zeros((sample_info.shape[0], numResampleLogX))
	logp_samples = np.zeros((sample_info.shape[0], numResampleLogX))
	logP_samples = np.zeros((sample_info.shape[0], numResampleLogX))
	P_samples = np.zeros((sample_info.shape[0], numResampleLogX))
	logz_estimates = np.zeros((numResampleLogX, 1))
	H_estimates = np.zeros((numResampleLogX, 1))

	# Find sandwiching level for each sample
	sandwich = sample_info[:,0].copy().astype('int')
	for i in xrange(0, sample.shape[0]):
		while sandwich[i] < levels.shape[0]-1 and logl_samples[i] > logl_levels[sandwich[i] + 1]:
			sandwich[i] += 1

	for z in xrange(0, numResampleLogX):
		# For each level
		for i in range(0, levels.shape[0]):
			# Find the samples sandwiched by this level
			which = np.nonzero(sandwich == i)[0]
			logl_samples_thisLevel = [] # (logl, tieBreaker, ID)
			for j in xrange(0, len(which)):
				logl_samples_thisLevel.append(copy.deepcopy(logl_samples[which[j]]))
			logl_samples_thisLevel = sorted(logl_samples_thisLevel)
			N = len(logl_samples_thisLevel)

			# Generate intermediate logx values
			logx_max = levels[i, 0]
			if i == levels.shape[0]-1:
				logx_min = -1E300
			else:
				logx_min = levels[i+1, 0]
			Umin = np.exp(logx_min - logx_max)

			if N == 0 or numResampleLogX > 1:
				U = Umin + (1. - Umin)*np.random.rand(len(which))
			else:
				U = Umin + (1. - Umin)*np.linspace(1./(N+1), 1. - 1./(N+1), N)
			logx_samples_thisLevel = np.sort(logx_max + np.log(U))[::-1]

			for j in xrange(0, which.size):
				logx_samples[logl_samples_thisLevel[j][2]][z] = logx_samples_thisLevel[j]

				if j != which.size - 1:
					left = logx_samples_thisLevel[j+1]
				elif i == levels.shape[0]-1:
					left = -1E300
				else:
					left = levels[i+1][0]
				
				if j != 0:
					right = logx_samples_thisLevel[j-1]
				else:
					right = levels[i][0]

				logp_samples[logl_samples_thisLevel[j][2]][z] = np.log(0.5) + logdiffexp(right, left)

		logl = sample_info[:,1]/temperature

		logp_samples[:,z] = logp_samples[:,z] - logsumexp(logp_samples[:,z])
		logP_samples[:,z] = logp_samples[:,z] + logl
		logz_estimates[z] = logsumexp(logP_samples[:,z])
		logP_samples[:,z] -= logz_estimates[z]
		P_samples[:,z] = np.exp(logP_samples[:,z])
		H_estimates[z] = -logz_estimates[z] + np.sum(P_samples[:,z]*logl)

		if plot:
			plt.figure(3)
			if z == 0:
				plt.subplot(2,1,1)
				plt.plot(logx_samples[:,z], sample_info[:,1], 'b.', markersize=1, label='Samples')
				plt.hold(True)
				plt.plot(levels[1:,0], levels[1:,1], 'r.', label='Levels')
				plt.legend(numpoints=1, loc='lower left')
				plt.title('Likelihood Curve')
				plt.ylabel(r'$\log(L)$')

				# Use all plotted logl values to set ylim
				combined_logl = np.hstack([sample_info[:,1], levels[1:, 1]])
				combined_logl = np.sort(combined_logl)
				lower = combined_logl[int(0.07*combined_logl.size)]
				upper = combined_logl[-1]
				diff = upper - lower
				lower -= 0.05*diff
				upper += 0.05*diff
				if zoom_in:
					plt.ylim([lower, upper])

				if numResampleLogX > 1:
					plt.draw()
				xlim = plt.gca().get_xlim()

		if plot:
			plt.subplot(2,1,2)
			plt.hold(False)
			plt.plot(logx_samples[:,z], P_samples[:,z], 'b.', markersize=1)
			plt.ylabel('Posterior Weights')
			plt.xlabel(r'$\log(X)$')
			plt.xlim(xlim)
			if numResampleLogX > 1:
				plt.draw()

			plt.show()
			#plt.savefig('galaxyfield_likelihood.pdf', bbox_inches='tight')

	P_samples = np.mean(P_samples, 1)
	P_samples = P_samples/np.sum(P_samples)
	logz_estimate = np.mean(logz_estimates)
	logz_error = np.std(logz_estimates)
	H_estimate = np.mean(H_estimates)
	H_error = np.std(H_estimates)
	ESS = np.exp(-np.sum(P_samples*np.log(P_samples+1E-300)))

	print("log(Z) = " + str(logz_estimate) + " +- " + str(logz_error))
	print("Information = " + str(H_estimate) + " +- " + str(H_error) + " nats.")
	print("Effective sample size = " + str(ESS))

	# Resample to uniform weight
	N = 300#max(300, int(ESS))
	posterior_sample = np.zeros((N, sample.shape[1]))
	w = P_samples
	w = w/np.max(w)
	if save:
		np.savetxt('run-'+filename+'/weights.txt', w) # Save weights
	for i in xrange(0, N):
		while True:
			which = np.random.randint(sample.shape[0])
			if np.random.rand() <= w[which]:
				break
		posterior_sample[i,:] = sample[which,:]
	if save:
		np.savetxt('run-'+filename+"/posterior_sample.txt", posterior_sample)
		print 'Saved Posterior Samples'

	if plot:
		if numResampleLogX > 1:
			plt.ioff()
		plt.show()

	return [logz_estimate, H_estimate, logx_samples]

import sys
postprocess(sys.argv[1])
