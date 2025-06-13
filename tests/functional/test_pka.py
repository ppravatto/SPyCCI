import pytest

from spycci.engines.xtb import XtbInput
from spycci.engines.orca import OrcaInput
from spycci.systems import System, Ensemble
from spycci.functions.pka import calculate_pka, calculate_pka_oxonium_scheme, auto_calculate_pka, run_pka_workflow
from os.path import dirname, abspath
from shutil import rmtree

import numpy as np
from numpy.testing import assert_almost_equal

# Get the path of the tests directory
TEST_DIR = dirname(abspath(__file__))


def test_calculate_pka_xtb():

    protonated = System(f"{TEST_DIR}/utils/xyz_files/acetic_acid.xyz", charge=0, spin=1)
    deprotonated = System(f"{TEST_DIR}/utils/xyz_files/deprotonated_acetic_acid.xyz", charge=-1, spin=1)

    xtb = XtbInput(solvent="water")
    xtb.opt(protonated, inplace=True)
    xtb.opt(deprotonated, inplace=True)

    try:
        pka = calculate_pka(protonated, deprotonated)

    except:
        assert False, "Unexpected exception raised during pka calculation"

    assert_almost_equal(pka, 8.401564242900081, decimal=3)
    assert_almost_equal(protonated.properties.pka, 8.401564242900081, decimal=3)

    rmtree("output_files")
    rmtree("error_files")


def test_calculate_pka_oxonium_scheme_xtb():

    protonated = System(f"{TEST_DIR}/utils/xyz_files/acetic_acid.xyz", charge=0, spin=1)
    deprotonated = System(f"{TEST_DIR}/utils/xyz_files/deprotonated_acetic_acid.xyz", charge=-1, spin=1)
    water = System(f"{TEST_DIR}/utils/xyz_files/water.xyz", charge=0, spin=1)
    oxonium = System(f"{TEST_DIR}/utils/xyz_files/oxonium.xyz", charge=1, spin=1)

    xtb = XtbInput(solvent="water")
    xtb.opt(protonated, inplace=True)
    xtb.opt(deprotonated, inplace=True)
    xtb.opt(water, inplace=True)
    xtb.opt(oxonium, inplace=True)

    try:
        pka = calculate_pka_oxonium_scheme(protonated, deprotonated, water, oxonium)

    except:
        assert False, "Unexpected exception raised during pka calculation"

    assert_almost_equal(pka, 13.22416853109027, decimal=3)
    assert_almost_equal(protonated.properties.pka, 13.22416853109027, decimal=3)

    rmtree("output_files")
    rmtree("error_files")


def test_auto_calculate_pka_xtb():

    protonated = System(f"{TEST_DIR}/utils/xyz_files/acetic_acid.xyz")
    xtb = XtbInput(solvent="water")

    try:
        pka, _ = auto_calculate_pka(
            protonated,
            method_el=xtb,
            method_vib=xtb,
            method_opt=xtb,
            ncores=2,
            maxcore=2000,
        )

    except:
        assert False, "Unexpected exception raised during pka calculation"

    assert_almost_equal(pka, 8.306140678635513, decimal=3)
    assert_almost_equal(protonated.properties.pka, 8.306140678635513, decimal=3)

    rmtree("output_files")
    rmtree("error_files")


def test_run_pka_workflow_different_geometry():

    protonated = System(f"{TEST_DIR}/utils/xyz_files/acetic_acid.xyz", charge=0, spin=1)
    deprotonated = System(f"{TEST_DIR}/utils/xyz_files/deprotonated_acetic_acid.xyz", charge=-1, spin=1)

    xtb = XtbInput(solvent="water")
    orca = OrcaInput(method="BP86", basis_set="def2-TZVPD", solvent="water")

    try:
        pka, free_energies = run_pka_workflow(
            protonated,
            deprotonated,
            orca,
            method_geometry=xtb,
            use_cosmors=True,
            ncores=4,
        )
    
    except:
        assert False, "Unexpected exception raised during pka calculation"

    expected_pka = {
        "direct": 7.415821942831063,
        "oxonium": 18.4104980835822,
        "oxonium COSMO-RS": 0.1687110148782882,
    }

    expected_free_energies = {
        "G(solv) Protonated": -229.16930255037,
        "G(solv) Deprotonated": -228.722438784737,
        "G(solv) Water": -76.47613139996601,
        "G(solv) Oxonium": -76.879179351375,
        "dG(COSMO-RS) Protonated": -0.011657871459,
        "dG(COSMO-RS) Deprotonated": -0.133906468434,
        "dG(COSMO-RS) Water": -0.012186990744,
        "dG(COSMO-RS) Oxonium": -0.172558918245,
        "G(vac) Protonated": -229.15909637338498,
        "G(vac) Deprotonated": -228.61163676684,
        "G(vac) Water": -76.464912575421,
        "G(vac) Oxonium": -76.72559529110801,
    }

    for key, value in expected_pka.items():
        assert_almost_equal(value, pka[key], decimal=3)

    for key, value in expected_free_energies.items():
        assert_almost_equal(value, free_energies[key], decimal=3)
    
    for key in pka.keys():
        if key not in expected_pka.keys():
            assert False, "Unexpected key found in pka dictionary"
    
    for key in free_energies.keys():
        if key not in expected_free_energies.keys():
            assert False, "Unexpected key found in free energies dictionary"
    
    rmtree("output_files")
    rmtree("error_files")


def test_run_pka_workflow_different_electronic():

    protonated = System(f"{TEST_DIR}/utils/xyz_files/acetic_acid.xyz", charge=0, spin=1)
    deprotonated = System(f"{TEST_DIR}/utils/xyz_files/deprotonated_acetic_acid.xyz", charge=-1, spin=1)

    xtb = XtbInput(solvent="water")
    orca = OrcaInput(method="BP86", basis_set="def2-TZVPD", solvent="water")

    try:
        pka, free_energies = run_pka_workflow(
            protonated,
            deprotonated,
            method_vibronic=xtb,
            method_electonic=orca,
            method_geometry=xtb,
            use_cosmors=True,
            ncores=4,
        )
    
    except:
        assert False, "Unexpected exception raised during pka calculation"

    expected_pka = {
        "direct": 7.83276723959946,
        "oxonium": 18.42137626296255,
        "oxonium COSMO-RS": 0.3984120920212615,
    }

    expected_free_energies = {
        "G(solv) Protonated": -229.171070549242,
        "G(solv) Deprotonated": -228.72330030332898,
        "G(solv) Water": -76.477315918202,
        "G(solv) Oxonium": -76.881246699654,
        "dG(COSMO-RS) Protonated": -0.011657871459,
        "dG(COSMO-RS) Deprotonated": -0.133906468434,
        "dG(COSMO-RS) Water": -0.012186990744,
        "dG(COSMO-RS) Oxonium": -0.172558918245,
        "G(vac) Protonated": -229.160591082023,
        "G(vac) Deprotonated": -228.61179837069201,
        "G(vac) Water": -76.466020027342,
        "G(vac) Oxonium": -76.727536454973,
    }

    for key, value in expected_pka.items():
        assert_almost_equal(value, pka[key], decimal=3)

    for key, value in expected_free_energies.items():
        assert_almost_equal(value, free_energies[key], decimal=3)
    
    for key in pka.keys():
        if key not in expected_pka.keys():
            assert False, "Unexpected key found in pka dictionary"
    
    for key in free_energies.keys():
        if key not in expected_free_energies.keys():
            assert False, "Unexpected key found in free energies dictionary"
    
    rmtree("output_files")
    rmtree("error_files")