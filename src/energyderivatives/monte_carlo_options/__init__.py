from ..base import GreeksFDM, Option as _Option
from ..utils import docstring_from
from ..vanillaoptions import GBSOption as _GBSOption

from .mc_innovations import *
from .mc_paths import *
from .mc_payoffs import *

import numpy as _np


class MonteCarloOption:  # _Option
    """
    Class for the valuation of options using Monte Carlo methods using passed innovation, path and
    payoff calculation classes that inherit from the classes Innovations, Path and Payoff respectively.
    Parent classes are defined within this module. See example below.

    Parameters
    ----------
    mc_paths : int
        Number of payoff paths to generate per mc_loop. Total number of monte carlo sample paths
        is mc_loops * mc_paths.
    mc_loops : int
        Number of times to generate mc_path number of monte carlo paths. Any positive number.
        Total number of monte carlo sample paths is mc_loops * mc_paths.
    path_length : int
        Number of time steps to maturity t. dt = t/path_length.
    S : float
        Level or index price.
    K : float
        Strike price.
    t : float
        Time-to-maturity in fractional years. i.e. 1/12 for 1 month, 1/252 for 1 business day, 1.0 for 1 year.
    r : float
        Risk-free-rate in decimal format (i.e. 0.01 for 1%).
    b : float
        Annualized cost-of-carry rate, e.g. 0.1 means 10%.
    sigma : float
        Annualized volatility of the underlying asset. Optional if calculating implied volatility.
        Required otherwise. By default None.
    Innovation : Innovations class
        An Innovations subclass that has a sample_innovation method for generating innovations for
        the path generation step. sample_innovation method must return an numpy array of shape
        (mc_paths, path_length). See parent definition below.
    Path : Path subclass
        A Path subclass that has a generate_path method for generating monte carlo paths using the
        innovations of the Innovation class. generate_path method must return a numpy array of
        shape (mc_paths, path_length). See parent definition below.
    Payoff : Payoff sublass
        A Payoff subclass that has both the call and put methods for calculation strike payoffs
        at option maturity. Class must be able to calculate the payoffs based on a numpy array
        of monte carlo paths and call and put methods must return numpy arrays of shape
        (mc_paths,). See parent definition below.
    trace : bool
        If True, it will return the average option value per mc_loop as well as the cumulative
        average of these averages. Only useful with mc_loops > 1. By default False.
    antithetic : bool
        If True, innovations generated from the Innovations class is combined with it's negative
        version (i.e. -1 * Innovations) to center the innovations around zero. Note if set to
        True, this will double the number of mc_paths. By default False.
    standardization : bool
        If True, the first (mean) and second (standard deviation) moments of the generated
        innovations are made to match 0 and 1 respectively to account for errors in a pseudo
        random number generator. By default False.
    eps : numpy array
        pregenerated innovations to be used instead of one generated by an innovation class. Note
        that the innovation class must still be passed. By default None. For testing purposes only.

    Notes
    -----
    Including a cost of carry term b, the model can
    used to price European Options on:

    b = r       stocks (Black and Scholes’ stock option model)
    b = r - q   stocks and stock indexes paying a continuous dividend yield q (Merton’s stock option model)
    b = 0       futures (Black’s futures option model)
    b = r - rf  currency options with foreign interst rate rf (Garman and Kohlhagen’s currency option model)

    Parent Classes
    --------------

    class Innovations(ABC):
        def __init__(self, mc_paths, path_length, eps=None):
            self.mc_paths = mc_paths
            self.path_length = path_length
            self._eps = eps  # for testing only

        @abstractmethod
        def sample_innovation(self, init=False):
            pass # must return a numpy array of shape (mc_paths, path_length)

    class Path(ABC):
        def __init__(self, epsilon, sigma, dt, b):
            self.epsilon = epsilon # array of innovations
            self.sigma = sigma
            self.dt = dt # calculated dt from t/path_length
            self.b = b

        @abstractmethod
        def generate_path(self):
            pass # must return a numpy array of shape (mc_paths, path_length)

    class Payoff(ABC):
        def __init__(self, path, S: float, K: float, t: float, r: float, b: float, sigma: float):
            self.path = path
            self.S = S
            self.K = K
            self.t = t
            self.r = r
            self.b = b
            self.sigma = sigma

        @abstractmethod
        def call(self):
            pass # must return an average payoff for each mc_loop

        @abstractmethod
        def put(self):
            pass # must return an average payoff for each mc_loop

    Returns
    -------
    MonteCarloOption object.

    Example
    -------
    >>> import energyderivatives as ed
    >>> from scipy.stats import qmc, norm
    >>> import numpy as np
    >>> from energyderivatives.monte_carlo_options import Innovations, Path, Payoff
    >>> S = 100
    >>> K = 100
    >>> t = 1 / 12
    >>> sigma = 0.4
    >>> r = 0.10
    >>> b = 0.1
    >>> path_length = 30
    >>> mc_paths = 5000
    >>> mc_loops = 50

    >>> class NormalSobolInnovations(Innovations):
            def sample_innovation(self, scramble=True):
                sobol = qmc.Sobol(self.path_length, scramble=scramble).random(self.mc_paths)
                if scramble == False:
                    # add new sample since if not scrambled first row is zero which leads to -inf when normalized
                    sobol = sobol[1:]
                    sobol = _np.append(
                        sobol,
                        qmc.Sobol(self.path_length, scramble=scramble).fast_forward(self.mc_paths).random(1),
                        axis=0,
                    )
                sobol = norm.ppf(sobol)
                return sobol

    >>> class WienerPath(Path):
            def generate_path(self, **kwargs):
                return (self.b - (self.sigma ** 2) / 2) * self.dt + self.sigma * np.sqrt(self.dt)  * self.epsilon

    >>> class PlainVanillaPayoff(Payoff):
            def call(self):
                St = self.S * np.exp(np.sum(self.path.generate_path(), axis=1))
                return np.exp(-self.r * self.t) * np.maximum(St - self.K, 0)

            def put(self):
                St = self.S * np.exp(np.sum(self.path.generate_path(), axis=1))
                return np.exp(-self.r * self.t) * np.maximum(self.K - St, 0)

    >>> opt = ed.monte_carlo_options.MonteCarloOption(
            mc_loops, path_length, mc_paths,
            S, K, t, r, b, sigma,
            NormalSobolInnovations, WienerPath, PlainVanillaPayoff,
            trace=False, antithetic=True, standardization=False
        )
    >>> print(opt.call().mean())
    >>> print(opt.put().mean())
    >>> opt.greeks(call=True) # not working yet

    References
    ----------
    [1] Haug E.G., The Complete Guide to Option Pricing Formulas

    """

    __name__ = "MCOption"
    __title__ = "Monte Carlo Simulation Option"

    def __init__(
        self,
        mc_loops: int,
        path_length: int,
        mc_paths: int,
        S: float,
        K: float,
        t: float,
        r: float,
        b: float,
        sigma: float = None,
        Innovation: Innovations = None,
        Path=None,
        Payoff=None,
        trace=False,
        antithetic=False,
        standardization=False,
        eps=None,
        **kwargs,
    ):

        self._mc_loops = mc_loops
        self._path_length = path_length
        self._mc_paths = mc_paths
        self._dt = t / path_length
        self._S = S
        self._K = K
        self._t = t
        self._r = r
        self._b = b
        self._sigma = sigma
        self._Innovation = Innovation(mc_paths, path_length, eps)
        self._Path = Path
        self._Payoff = Payoff
        self._trace = trace
        self._antithetic = antithetic
        self._standardization = standardization
        self._eps = eps
        self._kwargs = kwargs

    def call(self):
        """
        Returns an array of the average option call price per Monte Carlo Loop (mc_loop). Final option value
        is the average of the returned array.

        Returns
        -------
        numpy array

        Example
        -------
        >>> import energyderivatives as ed
        >>> inno = ed.monte_carlo_options.NormalSobolInnovations
        >>> path = ed.monte_carlo_options.WienerPath
        >>> payoff = ed.monte_carlo_options.PlainVanillaPayoff
        >>> opt = ed.monte_carlo_options.MonteCarloOption(50, 30, 5000,
                100, 100, 1/12, 0.1, 0.1, 0.4, inno, path, payoff)
        >>> opt.call()

        References
        ----------
        [1] Haug E.G., The Complete Guide to Option Pricing Formulas
        """
        return self._sim_mc(call=True)

    def put(self):
        """
        Returns an array of the average option out price per Monte Carlo Loop (mc_loop). Final option value
        is the average of the returned array.

        Returns
        -------
        numpy array

        Example
        -------
        >>> import energyderivatives as ed
        >>> inno = ed.monte_carlo_options.NormalSobolInnovations
        >>> path = ed.monte_carlo_options.WienerPath
        >>> payoff = ed.monte_carlo_options.PlainVanillaPayoff
        >>> opt = ed.monte_carlo_options.MonteCarloOption(50, 30, 5000,
                100, 100, 1/12, 0.1, 0.1, 0.4, inno, path, payoff)
        >>> opt.put()

        References
        ----------
        [1] Haug E.G., The Complete Guide to Option Pricing Formulas
        """

        return self._sim_mc(call=False)

    def _sim_mc(self, call=True):

        dt = self._dt
        trace = self._trace

        if trace:
            print("\nMonte Carlo Simulation Path:\n\n")
            print("\nLoop:\t", "No\t")

        iteration = _np.zeros(self._mc_loops)

        # MC Iteration Loop:

        for i in range(self._mc_loops):
            #     # if ( i > 1) init = FALSE
            # Generate Innovations:
            eps = self._Innovation.sample_innovation()

            # Use Antithetic Variates if requested:
            if self._antithetic:
                eps = _np.concatenate((eps, -eps))
            #     # Standardize Variates if requested:
            if self._standardization:
                eps = (eps - _np.mean(eps)) / _np.std(eps)

                # eps = (eps-mean(eps))/sqrt(var(as.vector(eps)))

            # Calculate for each path the option price:
            path = self._Path(eps, self._sigma, self._dt, self._b)

            # so I think the original fOptions function has an error. It calcs
            # the payoff along the wrong dimensions such that it only calcs
            # along path_length number of samples vs mc_paths. I think the t()
            # is the problem.

            if call == True:
                payoff = self._Payoff(
                    path, self._S, self._K, self._t, self._r, self._b, self._sigma
                ).call()
            else:
                payoff = self._Payoff(
                    path, self._S, self._K, self._t, self._r, self._b, self._sigma
                ).put()

            tmp = _np.mean(payoff)

            if tmp == _np.inf:
                import warnings

                warnings.warn(f"Warning: mc_loop {i} returned Inf.")
                return (eps, path, payoff)

            iteration[i] = tmp

            if trace:
                print(
                    "\nLoop:\t",
                    i,
                    "\t:",
                    iteration[i],
                    _np.sum(iteration) / (i + 1),
                    end="",
                )
        print("\n")

        return iteration
