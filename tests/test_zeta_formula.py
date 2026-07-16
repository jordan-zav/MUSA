import math

from musa.core import MUSA


def test_zeta_scale_factor_uses_floor_at_coarsest_regression_scale():
    zeta = MUSA._zeta_mother_scale(
        mother_scale=4000,
        eps=2000,
        eps_coarse=2000,
        eps_fine=250,
        m_total=100,
        m_finest=100,
        n_occupied=4,
        entropy=math.log(4),
        exponents=(1, 1, 1, 1),
        scale_floor=0.25,
    )

    coverage = 4 / 4
    mass_ratio = 1
    neff_ratio = 1
    scale_factor = 0.25
    assert math.isclose(zeta, coverage * mass_ratio * neff_ratio * scale_factor, rel_tol=1e-9)


def test_zeta_penalizes_concentrated_mass_with_effective_box_term():
    uniform = MUSA._zeta_mother_scale(
        mother_scale=4000,
        eps=1000,
        eps_coarse=2000,
        eps_fine=250,
        m_total=100,
        m_finest=100,
        n_occupied=4,
        entropy=math.log(4),
        exponents=(0, 0, 0, 1),
        scale_floor=0.25,
    )
    concentrated = MUSA._zeta_mother_scale(
        mother_scale=4000,
        eps=1000,
        eps_coarse=2000,
        eps_fine=250,
        m_total=100,
        m_finest=100,
        n_occupied=4,
        entropy=0.0,
        exponents=(0, 0, 0, 1),
        scale_floor=0.25,
    )

    assert math.isclose(uniform, 1.0, rel_tol=1e-9)
    assert math.isclose(concentrated, 0.25, rel_tol=1e-9)
