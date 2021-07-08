import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src/")

import energyderivatives as ed


def test_vanilla():

    opt_test = [
        (ed, "GBSOption", {"S": 10.0, "t": 1.0, "r": 0.02, "b": 0.01, "sigma": 0.2}),
        (
            ed,
            "BlackScholesOption",
            {"S": 10.0, "t": 1.0, "r": 0.02, "b": 0.01, "sigma": 0.2},
        ),
        (ed, "Black76Option", {"S": 10.0, "t": 1.0, "r": 0.02, "sigma": 0.2}),
    ]

    K = np.arange(8, 12)

    for test in opt_test:
        opt_array = getattr(test[0], test[1])(K=K, **test[2])
        opt = []
        for k_ind in K:
            opt.append(getattr(test[0], test[1])(K=k_ind, **test[2]))

        for i, _ in enumerate(opt):
            assert np.allclose(
                opt_array.call()[i], opt[i].call()
            ), f"{opt[i].__name__} failed call() test for passing arrays for K = {K[i]}"

        for i, _ in enumerate(opt):
            assert np.allclose(
                opt_array.put()[i], opt[i].put()
            ), f"{opt[i].__name__} failed put() test for passing arrays for K = {K[i]}"

        for i, _ in enumerate(opt):
            print(opt)
            assert np.allclose(
                opt_array.volatility(K - 5)[i], opt[i].volatility(K[i] - 5)
            ), f"{opt[i].__name__} failed volatility() test for passing arrays for K = {K[i]}"


if __name__ == "__main__":
    test_vanilla()
