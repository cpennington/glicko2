"""
Copyright (c) 2009 Ryan Kirkman

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import math

SCALE = 173.7178


def rating_to_mu(rating):
    return (rating - 1500) / SCALE


def mu_to_rating(mu):
    return (mu * SCALE) + 1500


def rd_to_phi(rd):
    return rd / SCALE


def phi_to_rd(phi):
    return phi * SCALE


class Player:
    # Class attribute
    # The system constant, which constrains
    # the change in volatility over time.
    _tau = 0.5

    def getRating(self):
        return mu_to_rating(self.mu)

    def setRating(self, rating):
        self.mu = rating_to_mu(rating)

    rating = property(getRating, setRating)

    def getRd(self):
        return phi_to_rd(self.phi)

    def setRd(self, rd):
        self.phi = rd_to_phi(rd)

    rd = property(getRd, setRd)

    def __init__(self, rating=1500, rd=350, vol=0.06):
        # For testing purposes, preload the values
        # assigned to an unrated player.
        self.rating = rating
        self.rd = rd
        self.vol = vol

    def _preRatingRD(self):
        """Calculates and updates the player's rating deviation for the
        beginning of a rating period.

        preRatingRD() -> None

        """
        self.phi = math.sqrt(math.pow(self.phi, 2) + math.pow(self.vol, 2))

    def win_prob(self, other):
        """Calculate the chance of winning a game against another player."""
        return 1 / (
            1
            + math.exp(
                -1
                * self._g(math.sqrt(self.phi**2 + other.phi**2))
                * (self.mu - other.mu)
            )
        )

    def update_player(self, rating_list, RD_list, outcome_list):
        """Calculates the new rating and rating deviation of the player.

        update_player(list[int], list[int], list[bool]) -> None

        """
        # Convert the rating and rating deviation values for internal use.
        rating_list = [rating_to_mu(x) for x in rating_list]
        RD_list = [rd_to_phi(x) for x in RD_list]

        v = self._v(rating_list, RD_list)
        self.vol = self._newVol(rating_list, RD_list, outcome_list, v)
        self._preRatingRD()

        self.phi = 1 / math.sqrt((1 / math.pow(self.phi, 2)) + (1 / v))

        tempSum = 0
        for i in range(len(rating_list)):
            tempSum += self._g(RD_list[i]) * (
                outcome_list[i] - self._E(rating_list[i], RD_list[i])
            )
        self.mu += math.pow(self.phi, 2) * tempSum

    # step 5
    def _newVol(self, rating_list, RD_list, outcome_list, v):
        """Calculating the new volatility as per the Glicko2 system.

        Updated for Feb 22, 2012 revision. -Leo

        _newVol(list, list, list, float) -> float

        """
        # step 1
        a = math.log(self.vol**2)
        eps = 0.000001
        A = a

        # step 2
        B = None
        delta = self._delta(rating_list, RD_list, outcome_list, v)
        tau = self._tau
        if (delta**2) > ((self.phi**2) + v):
            B = math.log(delta**2 - self.phi**2 - v)
        else:
            k = 1
            while self._f(a - k * math.sqrt(tau**2), delta, v, a) < 0:
                k = k + 1
            B = a - k * math.sqrt(tau**2)

        # step 3
        fA = self._f(A, delta, v, a)
        fB = self._f(B, delta, v, a)

        # step 4
        while math.fabs(B - A) > eps:
            # a
            C = A + ((A - B) * fA) / (fB - fA)
            fC = self._f(C, delta, v, a)
            # b
            if fC * fB < 0:
                A = B
                fA = fB
            else:
                fA = fA / 2.0
            # c
            B = C
            fB = fC

        # step 5
        return math.exp(A / 2)

    def _f(self, x, delta, v, a):
        ex = math.exp(x)
        num1 = ex * (delta**2 - self.mu**2 - v - ex)
        denom1 = 2 * ((self.mu**2 + v + ex) ** 2)
        return (num1 / denom1) - ((x - a) / (self._tau**2))

    def _delta(self, rating_list, RD_list, outcome_list, v):
        """The delta function of the Glicko2 system.

        _delta(list, list, list) -> float

        """
        tempSum = 0
        for i in range(len(rating_list)):
            tempSum += self._g(RD_list[i]) * (
                outcome_list[i] - self._E(rating_list[i], RD_list[i])
            )
        return v * tempSum

    def _v(self, rating_list, RD_list):
        """The v function of the Glicko2 system.

        _v(list[int], list[int]) -> float

        """
        tempSum = 0
        for i in range(len(rating_list)):
            tempE = self._E(rating_list[i], RD_list[i])
            tempSum += math.pow(self._g(RD_list[i]), 2) * tempE * (1 - tempE)
        return 1 / tempSum

    def _E(self, p2mu, p2phi):
        """The Glicko E function.

        _E(int) -> float

        """
        return 1 / (1 + math.exp(-1 * self._g(p2phi) * (self.mu - p2mu)))

    def _g(self, RD):
        """The Glicko2 g(RD) function.

        _g() -> float

        """
        return 1 / math.sqrt(1 + 3 * math.pow(RD, 2) / math.pow(math.pi, 2))

    def did_not_compete(self):
        """Applies Step 6 of the algorithm. Use this for
        players who did not compete in the rating period.

        did_not_compete() -> None

        """
        self._preRatingRD()
