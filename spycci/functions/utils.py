import logging
from typing import Optional

from spycci.systems import Ensemble
from spycci.systems import System

from spycci.core.geometry import MolecularGeometry

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# A list of useful molecules that can be used by library functions

WATER = [
    ["O", -5.02534, 1.26595, 0.01097],
    ["H", -4.05210, 1.22164, -0.01263],
    ["H", -5.30240, 0.44124, -0.42809],
]

OXONIUM = [
    ["O", -7.37112, 1.56763, 0.10145],
    ["H", -6.40989, 1.39069, -0.03899],
    ["H", -7.67217, 2.18471, -0.60766],
    ["H", -7.85266, 0.71353, -0.01396],
]

AVAILABLE_MOLECULES = {
    "water" : WATER,
    "oxonium" : OXONIUM
}

# -------------------------------------------------------------------------------

def retrieve_structure(molname: str) -> MolecularGeometry:
    """
    Returns the `MolecularGeometry` object encoding the coordinates of
    the user selected molecule.

    Arguments
    ---------
    molname : str
        The name of the desired molecule.
    
    Raises
    ------
    RuntimeError
        Exception raised if the molecule requested is not available.
    
    Returns
    -------
    MolecularGeometry
        The `MolecularGeometry` object encoding the structure of the molecule.
    """
    if molname not in AVAILABLE_MOLECULES.keys():
        msg = f"Molecule '{molname}' is not available."
        raise RuntimeError(msg)

    mol = MolecularGeometry()
    for line in AVAILABLE_MOLECULES[molname]:
        mol.append(line[0], line[1::])
    
    return mol


def check_structure_acid_base_pair(protonated: System, deprotonated: System) -> None:
    """
    Checks if the provided `protonated` and `deprotonated` objects are compatible with each other and
    with a pKa calculation. If validation fails an exception is raised.

    Parameters
    ----------
    protonated : System object
        The molecule in the protonated form
    deprotonated : System object
        The molecule in the deprotonated form

    Raises
    ------
    TypeError
        Exception raised if either of the objects type is different from `System`
    RuntimeError
        Excpetion raised if the atom count and charge variation are not compatible.
    """
    # Check if the objects are instances of `System`
    if type(protonated) == Ensemble or type(deprotonated) == Ensemble:
        msg = "The calculation of pKa for Ensemble objects is currently not supported."
        logger.error(msg)
        raise TypeError(msg)
    elif type(protonated) != System or type(deprotonated) != System:
        msg = "The calculation of pKa requires System type arguments."
        logger.error(msg)
        raise TypeError(msg)

    # Check that the atomcount of the two molecules matches
    if protonated.geometry.atomcount - deprotonated.geometry.atomcount != 1:
        msg = f"{protonated.name} deprotomer differs for more than 1 atom."
        logger.error(msg)
        raise RuntimeError(msg)

    # Check that the molecular charge of the deprotomer is 1 unit less than the protonated one
    if deprotonated.charge - protonated.charge != -1:
        msg = f"{protonated.name} deprotomer differs for more than 1 unit of charge."
        logger.error(msg)
        raise RuntimeError(msg)


def validate_acid_base_pair(
    protonated: System,
    deprotonated: System,
    water: Optional[System] = None,
    oxonium: Optional[System] = None,
) -> bool:
    """
    Checks if the provided `protonated` and `deprotonated` objects are compatible with each other and
    with a pKa calculation and verify the matching between levels of theory used in the computation.
    The function also accepts a `water` and `oxonium` object as optionals to verify the compatibility
    of the levels of theory in case of the oxonium scheme. If validation fails an exception is raised.
    The function returns a bool value correspondent to the availability of vibronic calculations.

    Parameters
    ----------
    protonated : System object
        The molecule in the protonated form
    deprotonated : System object
        The molecule in the deprotonated form
    water : Optional[System]
        The water molecule to be used in the calculation
    oxonium : Optional[System]
        The oxonium molecule to be used in the calculation

    Raises
    ------
    TypeError
        Exception raised if either of the objects type is different from `System`
    RuntimeError
        Excpetion raised if the electronic level of theory is not found

    Returns
    -------
    bool
        True if the two system have appropriate and matching vibronic levels of theory. False otherwise.
    """
    # Check if the user provided both water and oxonium and check the structures
    if oxonium is None and water is None:
        pass
    elif None in [oxonium, water]:
        msg = "water and oxonium molecules must be checked simultaneously."
        logger.error(msg)
        raise RuntimeError(msg)

    # Check the provided structures for type, atomcount and charge
    check_structure_acid_base_pair(protonated, deprotonated)

    # Check that both the species have an electronic energy value associated
    if protonated.properties.electronic_energy is None:
        msg = "Electronic energy not found for protonated molecule."
        logger.error(msg)
        raise RuntimeError(msg)

    if deprotonated.properties.electronic_energy is None:
        msg = "Electronic energy not found for deprotonated molecule."
        logger.error(msg)
        raise RuntimeError(msg)

    # Check if the electronic level of theory for both molecules match
    elot_protonated = protonated.properties.level_of_theory_electronic
    elot_deprotonated = deprotonated.properties.level_of_theory_electronic
    if elot_protonated != elot_deprotonated:
        msg = "Mismatch found between electronic levels of theory."
        logger.error(msg)
        raise RuntimeError(msg)

    # Check, if povided, the water and oxonium molecules
    if oxonium and water:

        # Check the provided structures for type, atomcount and charge
        check_structure_acid_base_pair(oxonium, water)

        # Check that both the species have an electronic energy value associated
        if water.properties.electronic_energy is None:
            msg = "Electronic energy not found for water molecule."
            logger.error(msg)
            raise RuntimeError(msg)

        if oxonium.properties.electronic_energy is None:
            msg = "Electronic energy not found for oxonium ion."
            logger.error(msg)
            raise RuntimeError(msg)

        # Check if the electronic level of theory for both molecules match
        elot_water = water.properties.level_of_theory_electronic
        elot_oxonium = oxonium.properties.level_of_theory_electronic
        if elot_water != elot_oxonium or elot_water != elot_protonated:
            msg = "Mismatch found between electronic levels of theory."
            logger.error(msg)
            raise RuntimeError(msg)

    # Check if the species have vibronic energy values associated
    if (
        protonated.properties.vibronic_energy is None
        or deprotonated.properties.vibronic_energy is None
    ):
        msg = "Vibronic energies not found. The pKa calculation will be executed with only electronic energies"
        logger.warning(msg)
        return False

    if oxonium and water:

        if (
            water.properties.vibronic_energy is None
            or oxonium.properties.vibronic_energy is None
        ):
            msg = "Vibronic energies not found. The pKa calculation will be executed with only electronic energies"
            logger.warning(msg)
            return False

    # Check if the level of theory for vibronic calculation is the same
    vlot_protonated = protonated.properties.level_of_theory_vibronic
    vlot_deprotonated = deprotonated.properties.level_of_theory_vibronic
    if vlot_protonated == vlot_deprotonated:

        if oxonium and water:
            vlot_water = water.properties.level_of_theory_vibronic
            vlot_oxonium = oxonium.properties.level_of_theory_vibronic
            if vlot_protonated != vlot_water or vlot_protonated != vlot_oxonium:
                msg = "Vibronic energies not found. The pKa calculation will be executed with only electronic energies"
                logger.warning(msg)
                return False

        if elot_protonated != vlot_protonated:
            msg = f"Vibronic level of theory ({vlot_protonated}) is different form the electronic one ({elot_protonated}). The pKa calculation will be executed anyway."
            logger.warning(msg)

        return True

    else:
        msg = "Vibronic energies not found. The pKa calculation will be executed with only electronic energies"
        logger.warning(msg)
        return False