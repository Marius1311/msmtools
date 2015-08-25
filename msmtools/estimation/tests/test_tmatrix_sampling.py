from __future__ import absolute_import
from six.moves import range
# Copyright (c) 2015, 2014 Computational Molecular Biology Group, Free University
# Berlin, 14195 Berlin, Germany.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS IS''
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

r"""Unit tests for the transition_matrix module

.. moduleauthor:: B.Trendelkamp-Schroer <benjamin DOT trendelkamp-schroer AT fu-berlin DOT de>
.. moduleauthor:: Frank Noe <frank DOT noe AT fu-berlin DOT de>

"""

import unittest
import warnings

import numpy as np
from msmtools.util.numeric import assert_allclose
import scipy.sparse

from scipy.special import beta, betainc
from scipy.integrate import quad

from msmtools.estimation import sample_tmatrix, tmatrix_sampler
from msmtools.analysis import is_transition_matrix

class TestTransitionMatrixSampling(unittest.TestCase):
    def setUp(self):
        self.C = np.array([[7,1],
                           [2,2]])

    def test_sample_nonrev_1(self):
        P = sample_tmatrix(self.C)
        assert np.all(P.shape == self.C.shape)
        assert is_transition_matrix(P)

        # same with boject
        sampler = tmatrix_sampler(self.C)
        P = sampler.sample()
        assert np.all(P.shape == self.C.shape)
        assert is_transition_matrix(P)

    def test_sample_nonrev_10(self):
        sampler = tmatrix_sampler(self.C)
        Ps = sampler.sample(nsamples=10)
        assert len(Ps) == 10
        for i in range(10):
            assert np.all(Ps[i].shape == self.C.shape)
            assert is_transition_matrix(Ps[i])

class TestAnalyticalDistribution(unittest.TestCase):

    def setUp(self):
        """Safe random state"""
        self.state = np.random.get_state()
        """Set seed to enforce deterministic behavior"""
        np.random.seed(42)
        

        self.C = np.array([[5, 2], [3, 10]])
        self.pi = np.array([0.25, 0.75])
        self.N = 10000

        self.nx = 10
        self.xedges = np.linspace(0.0, 1.0, self.nx+1)
        dx = self.xedges[1] - self.xedges[0]
        self.xcenters = self.xedges[0:-1] + 0.5 * dx

        self.ny = 10
        self.yedges = np.linspace(0.0, 1.0, self.ny+1)
        dy = self.yedges[1] - self.yedges[0]
        self.ycenters = self.yedges[0:-1] + 0.5 * dy

    def tearDown(self):
        """Reset state"""
        np.random.set_state(self.state)

    def probabilities_rev(self, xedges, yedges):
        C = self.C
        px = betainc(C[0, 1], C[0, 0], xedges[1:]) - betainc(C[0, 1], C[0, 0], xedges[0:-1])
        py = betainc(C[1, 0], C[1, 1], yedges[1:]) - betainc(C[1, 0], C[1, 1], yedges[0:-1])
        return px[:,np.newaxis] * py[np.newaxis, :]

    def posterior_revpi(self, x, C, pi):
        z = (1.0-x)**C[0, 0] * x**C[0, 1] * pi[0]/pi[1] *x**C[1, 0] *\
            (1.0 - pi[0]/pi[1] * x)**C[1, 1]    
        return z

    def probabilities_revpi(self, xedges):
        Cp = self.C - np.array([[1, 1], [0, 1]])
        pi = self.pi
        N = xedges.shape[0]
        w = np.zeros(N-1)
        for i in range(N-1):
            w[i] = quad(self.posterior_revpi, xedges[i], xedges[i+1], args=(Cp, pi))[0]
        return w/w.sum()                    

    def test_rev(self):
        N = self.N
        sampler = tmatrix_sampler(self.C, reversible=True)
        M = self.C.shape[0]
        T_sample = np.zeros((N, M, M))
        for i in range(N):
            T_sample[i, :, :] = sampler.sample()
        p_12 = T_sample[:, 0, 1]
        p_21 = T_sample[:, 1, 0]
        H, xed, yed = np.histogram2d(p_12, p_21, bins=(self.xedges, self.yedges))        
        P_sampled =  H/self.N
        P_analytical = self.probabilities_rev(self.xedges, self.yedges)
        
        self.assertTrue(np.all(np.abs(P_sampled - P_analytical) < 0.01))
        
    def test_revpi(self):
        N = self.N
        sampler = tmatrix_sampler(self.C, reversible=True, mu=self.pi)
        M = self.C.shape[0]
        T_sample = np.zeros((N, M, M))
        for i in range(N):
            T_sample[i, :, :] = sampler.sample()
        H, xed = np.histogram(T_sample[:, 0, 1], self.xedges)
        P_sampled =  1.0*H/self.N
        P_analytical = self.probabilities_revpi(self.xedges)
        self.assertTrue(np.all( np.abs(P_sampled - P_analytical) < 0.01 ))


if __name__ == "__main__":
    unittest.main()
