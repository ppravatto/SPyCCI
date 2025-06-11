import logging
from copy import deepcopy
from typing import Union, Optional, Dict, Tuple

from spycci.systems import System
from spycci.core.base import Engine
from spycci.engines.xtb import XtbInput
from spycci.engines.orca import OrcaInput
from spycci.wrappers.crest import deprotonate
from spycci.tools.reorderenergies import reorder_energies
from spycci.functions.utils import retrieve_structure, validate_acid_base_pair, check_structure_acid_base_pair

import spycci.constants as scon
import numpy as np

logger = logging.getLogger(__name__)



def calculate_pka(protonated: System, deprotonated: System):
    """
    Calculates the pKa of a molecule using the direct method. The function expects as arguments
    the protonated and deprotonated forms of the molecule as a `System` objects for which the
    energies must have already been computed.

    Parameters
    ----------
    protonated : System object
        molecule in the protonated form
    deprotonated : System object
        molecule in the deprotonated form

    Returns
    -------
    pKa : float
        pKa of the molecule.
    """
    # Validate systems and check if vibronic energies are available
    with_vibronic = validate_acid_base_pair(protonated, deprotonated)

    # Extract electronic energies
    protonated_energy = protonated.properties.electronic_energy * scon.Eh_to_kcalmol
    deprotonated_energy = deprotonated.properties.electronic_energy * scon.Eh_to_kcalmol

    # If available consider vibronic energies
    if with_vibronic:
        protonated_energy += protonated.properties.vibronic_energy * scon.Eh_to_kcalmol
        deprotonated_energy += (
            deprotonated.properties.vibronic_energy * scon.Eh_to_kcalmol
        )

    # If gfn2 from xTB is used consider an additional correction factor for the proton self energy
    proton_self_energy = 0
    if "gfn2" in protonated.properties.level_of_theory_electronic:
        proton_self_energy = 164.22  # kcal/mol

    # Compute the pKa and set it as a property of the protonated molecule
    pka = (
        (
            deprotonated_energy
            + (scon.proton_hydration_free_energy + proton_self_energy)
            - protonated_energy
        )
    ) / (np.log(10.0) * scon.R * 298.15 / scon.kcal_to_J)

    protonated.properties.set_pka(
        value=pka,
        electronic_engine=protonated.properties.level_of_theory_electronic,
        vibronic_engine=protonated.properties.level_of_theory_vibronic,
    )

    return pka


def calculate_pka_oxonium_scheme(
    protonated: System, deprotonated: System, water: System, oxonium: System
):
    """
    Calculates the pKa of a molecule using the oxonium method. The function expects as arguments
    the protonated and deprotonated forms of the molecule as a `System` objects for which the
    energies must have already been computed.

    Parameters
    ----------
    protonated : System object
        molecule in the protonated form
    deprotonated : System object
        molecule in the deprotonated form

    Returns
    -------
    pKa : float
        pKa of the molecule.
    """
    # Validate systems and check if vibronic energies are available
    with_vibronic = validate_acid_base_pair(protonated, deprotonated)

    # Extract electronic energies
    protonated_energy = protonated.properties.electronic_energy * scon.Eh_to_kcalmol
    deprotonated_energy = deprotonated.properties.electronic_energy * scon.Eh_to_kcalmol
    water_energy = water.properties.electronic_energy * scon.Eh_to_kcalmol
    oxonium_energy = oxonium.properties.electronic_energy * scon.Eh_to_kcalmol

    # If available consider vibronic energies
    if with_vibronic:
        protonated_energy += protonated.properties.vibronic_energy * scon.Eh_to_kcalmol
        deprotonated_energy += (
            deprotonated.properties.vibronic_energy * scon.Eh_to_kcalmol
        )
        water_energy += water.properties.vibronic_energy * scon.Eh_to_kcalmol
        oxonium_energy += oxonium.properties.vibronic_energy * scon.Eh_to_kcalmol

    # Compute the pKa and set it as a property of the protonated molecule
    pka = (
        (deprotonated_energy + oxonium_energy - protonated_energy - water_energy)
    ) / (np.log(10.0) * scon.R * 298.15 / scon.kcal_to_J) - np.log10(997.0 / 18.01528)

    protonated.properties.set_pka(
        value=pka,
        electronic_engine=protonated.properties.level_of_theory_electronic,
        vibronic_engine=protonated.properties.level_of_theory_vibronic,
    )

    return pka


def run_pKa_workflow(
    protonated: System,
    deprotonated: System,
    method_geometry: Union[XtbInput, OrcaInput],
    method_vibronic: Union[XtbInput, OrcaInput],
    method_electonic: Optional[Union[XtbInput, OrcaInput]] = None,
    use_cosmors: bool = False,
    use_engine_settings: bool = False,
    ncores: Optional[int] = None,
    maxcore: int = 350,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    The function runs a complete pKa workflow and retuns the pKa values, computed with different schemes, 
    and all the computed free energies. The method runs a geometry optimization of both the protonated and
    deprotonated species in solvent (water). On the obtained geometries a frequecy calculation and, if necessaty,
    a single point calculation are carried out to compute the Gibbs free energies for all the species. 
    Water and Oxonium ion are automatically generated and optimized if required. The function then computes
    the pKa using the direct scheme and the oxonium scheme. If the `use_cosmors` option is used, the function
    also computes frequencies in vacuum and solvation free energies using OpenCOSMO-RS interface (requires orca>=6.0.0).
    The COSMO-RS calculation are then used to obtain the corresponding pKa using the oxonium method.

    Arguments
    ---------
    protonated : System
        The protonated system for which the pKa must be computed
    deprotonated : System
        The deprotomer generated during the dissociation reaction
    method_geometry : Union[XtbInput, OrcaInput]
        The engine to be used to run the geometry optimizations
    method_vibronic: Union[XtbInput, OrcaInput]
        The engine to be used to run the frequency calculations.
    method_electonic : Optional[Union[XtbInput, OrcaInput]]
        The engine to be used to run the electronic calculations. If set to `None` (default) will use electronic 
        energy computed by the `method_vibronic` engine. Please notice that, if the electronic method is different
        from the vibronic one, the computed Gibbs Free energy will be a mix of two different levels of theory (not
        advaisable)
    use_cosmors : bool
        If set to `True` will use OpenCOSMO-RS to compute solvation energies
    use_engine_settings : bool
        If set to `True` will use the engine level of theory to run the COSMO-RS calculation (not advisable)
    ncores : Optional[int]
        The number of cores to be used in the calculations. If set to `None` (default) will use
        the maximun number of available cores.
    maxcore: int (optional)
        For the engines that supprots it, the memory assigned to each core used in the
        computation.

    Retruns
    -------
    Dict[str, float]
        The dictionary containing all the computed pKa labelled by the name of the scheme employed.
        The possible labels are: 'direct', 'oxonium' and 'oxonium COSMO-RS'.
    Dict[str, float]
        The dictionary containing all the Gibbs Free energies used in the computations.
    """
    # Check if the given structures are compatible with a pKa calculation
    check_structure_acid_base_pair(protonated, deprotonated)

    # Check if the method to be used for geometry optimization is xtb or orca
    if type(method_geometry) not in [XtbInput, OrcaInput]:
        raise TypeError("The geometry optimization method must be xTB or orca.")

    # Check if the method to be used for frequency calculations is xtb or orca
    if type(method_vibronic) not in [XtbInput, OrcaInput]:
        raise TypeError("The frequency calculation method must be xTB or orca.")
    
    # Check if the method to be used for energy calculations is xtb or orca
    if type(method_electonic) not in [XtbInput, OrcaInput] and method_electonic is not None:
        raise TypeError("The energy calculation method must be xTB or orca.")

    # Define structures of water and oxonium ion
    water_xyz = retrieve_structure("water")
    water = System("water", charge=0, spin=1, geometry=water_xyz)

    oxonium_xyz = retrieve_structure("oxonium")
    oxonium = System("oxonium", charge=1, spin=1, geometry=oxonium_xyz)

    # Create an empty dictionary to store the computed pKas and Gibbs free energies
    computed_pka, free_energies = {}, {}

    # Run geometry optimization for all structures in solvent
    protonated_sol = method_geometry.opt(protonated, ncores=ncores, maxcore=maxcore)
    deprotonated_sol = method_geometry.opt(deprotonated, ncores=ncores, maxcore=maxcore)
    water_sol = method_geometry.opt(water, ncores=ncores, maxcore=maxcore)
    oxonium_sol = method_geometry.opt(oxonium, ncores=ncores, maxcore=maxcore)

    # Run frequency calculation for all structures in solvent
    if method_vibronic != method_geometry:
        method_vibronic.freq(protonated_sol, ncores=ncores, maxcore=maxcore, inplace=True)
        method_vibronic.freq(deprotonated_sol, ncores=ncores, maxcore=maxcore, inplace=True)
        method_vibronic.freq(water_sol, ncores=ncores, maxcore=maxcore, inplace=True)
        method_vibronic.freq(oxonium_sol, ncores=ncores, maxcore=maxcore, inplace=True)
    
    # If required run a single point calculation in solvent
    if method_electonic is not None and method_electonic != method_vibronic:
        method_electonic.spe(protonated_sol, ncores=ncores, maxcore=maxcore, inplace=True)
        method_electonic.spe(deprotonated_sol, ncores=ncores, maxcore=maxcore, inplace=True)
        method_electonic.spe(water_sol, ncores=ncores, maxcore=maxcore, inplace=True)
        method_electonic.spe(oxonium_sol, ncores=ncores, maxcore=maxcore, inplace=True)
    
    # Extract the Gibbs Free Energies from the obtained systems as E(el) + G-E(el)
    G_protonated_sol = protonated_sol.properties.electronic_energy
    G_deprotonated_sol = deprotonated_sol.properties.electronic_energy
    G_water_sol = water_sol.properties.electronic_energy
    G_oxonium_sol = oxonium_sol.properties.electronic_energy

    G_protonated_sol += protonated_sol.properties.vibronic_energy
    G_deprotonated_sol += deprotonated_sol.properties.vibronic_energy
    G_water_sol += water_sol.properties.vibronic_energy
    G_oxonium_sol += oxonium_sol.properties.vibronic_energy

    # Store the computed Gibbs Free Energies for the calculations in solvent
    free_energies["G(solv) Protonated"] = G_protonated_sol
    free_energies["G(solv) Deprotonated"] = G_deprotonated_sol
    free_energies["G(solv) Water"] = G_water_sol
    free_energies["G(solv) Oxonium"] = G_oxonium_sol

    # Calculate the pKa using the direct scheme
    pKa_direct = calculate_pka(protonated_sol, deprotonated_sol)
    computed_pka["direct"] = pKa_direct

    # Calculate the pKa using the oxonium scheme
    pKa_oxonium = calculate_pka_oxonium_scheme(protonated_sol, deprotonated_sol, water_sol, oxonium_sol)
    computed_pka["oxonium"] = pKa_oxonium

    # If required run the cosmors based schemes
    method_cosmors = method_electonic if method_electonic else method_vibronic
    if use_cosmors and type(method_cosmors)==OrcaInput:

        # Run COSMO-RS calculation for all molecules
        dG_solv_prot = method_cosmors.cosmors(protonated_sol, use_engine_settings=use_engine_settings, ncores=ncores, maxcore=maxcore)
        dG_solv_deprot = method_cosmors.cosmors(deprotonated_sol, use_engine_settings=use_engine_settings, ncores=ncores, maxcore=maxcore)
        dG_solv_water = method_cosmors.cosmors(water_sol, use_engine_settings=use_engine_settings, ncores=ncores, maxcore=maxcore)
        dG_solv_oxonium = method_cosmors.cosmors(oxonium_sol, use_engine_settings=use_engine_settings, ncores=ncores, maxcore=maxcore)

        # Store the solvation free energies computed with OpenCOSMO-RS
        free_energies["dG(COSMO-RS) Protonated"] = dG_solv_prot
        free_energies["dG(COSMO-RS) Deprotonated"] = dG_solv_deprot
        free_energies["dG(COSMO-RS) Water"] = dG_solv_water
        free_energies["dG(COSMO-RS) Oxonium"] = dG_solv_oxonium

        # Create an engine for the frequency calculations in vacuum
        method_vibronic_vac = deepcopy(method_vibronic)
        method_vibronic_vac.solvent = None

        # Run frequency calculation for all structures in vacuum
        protonated_vac = method_vibronic_vac.freq(protonated_sol, ncores=ncores, maxcore=maxcore)
        deprotonated_vac = method_vibronic_vac.freq(deprotonated_sol, ncores=ncores, maxcore=maxcore)
        water_vac = method_vibronic_vac.freq(water_sol, ncores=ncores, maxcore=maxcore)
        oxonium_vac = method_vibronic_vac.freq(oxonium_sol, ncores=ncores, maxcore=maxcore)

        # If required perform a single point calculation in vacuum
        if method_electonic is not None and method_electonic != method_vibronic:

            # Create an engine for the electronic calculations in vacuum
            method_electonic_vac = deepcopy(method_electonic)
            method_electonic_vac.solvent = None

            # Run frequency calculation for all structures in vacuum
            method_electonic_vac.spe(protonated_vac, ncores=ncores, maxcore=maxcore, inplace=True)
            method_electonic_vac.spe(deprotonated_vac, ncores=ncores, maxcore=maxcore, inplace=True)
            method_electonic_vac.spe(water_vac, ncores=ncores, maxcore=maxcore, inplace=True)
            method_electonic_vac.spe(oxonium_vac, ncores=ncores, maxcore=maxcore, inplace=True)

        # Extract the Gibbs Free Energies from the obtained systems as E(el) + G-E(el)
        G_protonated_vac = protonated_vac.properties.electronic_energy
        G_deprotonated_vac = deprotonated_vac.properties.electronic_energy
        G_water_vac = water_vac.properties.electronic_energy
        G_oxonium_vac = oxonium_vac.properties.electronic_energy

        G_protonated_vac += protonated_vac.properties.vibronic_energy
        G_deprotonated_vac += deprotonated_vac.properties.vibronic_energy
        G_water_vac += water_vac.properties.vibronic_energy
        G_oxonium_vac += oxonium_vac.properties.vibronic_energy

        # Store the Gibbs free energies computed in vacuum
        free_energies["G(vac) Protonated"] = G_protonated_vac
        free_energies["G(vac) Deprotonated"] = G_deprotonated_vac
        free_energies["G(vac) Water"] = G_water_vac
        free_energies["G(vac) Oxonium"] = G_oxonium_vac

        # Compute the reaction free energy in vacuum
        dG_vac = G_deprotonated_vac + G_oxonium_vac - G_protonated_vac - G_water_vac

        # Compute the difference in solvation free energy from OpenCOSMO-RS
        ddG_solv = dG_solv_deprot + dG_solv_oxonium - dG_solv_prot - dG_solv_water
        
        # Compute the corrected free energy in solvent and the corresponding pKa
        dG_cosmors = (dG_vac + ddG_solv) * scon.Eh_to_kcalmol
        pKa_cosmo = (dG_cosmors  / (np.log(10.0) * scon.R * 298.15 / scon.kcal_to_J)) - np.log10(997.0 / 18.01528)
        computed_pka["oxonium COSMO-RS"] = pKa_cosmo

    elif use_cosmors:
            logger.warning("COSMO-RS calculations can be run only by OrcaInput engine as electronic method.")    

    return computed_pka, free_energies


def auto_calculate_pka(
    protonated: System,
    method_el: Engine,
    method_vib: Engine = None,
    method_opt: Engine = None,
    ncores: int = None,
    maxcore: int = 350,
):
    """
    Automatically calculates the pKa of a given `protonated` molecule. The routine computes
    all the deprotomers of the molecule using CREST, orders the deprotomers according to
    their energy computed with a user-defined level of theory and calculates the pKa.

    Arguments
    ---------
    protonated: System
        The protonated molecule for which the pKa must be computed
    method_el: Engine
        The computational engine to be used in the electronic level of theory calculations
    method_vib: Engine (optional)
        The computational engine to be used in the vibronic level of theory calculations. If
        set to None (default) the pKa will be computed without the vibronic contributions.
    method_opt: Engine (optional)
        The computational engine to be used in the geometry optimization of the protonated
        molecule and its deprotomers. If set to None (default) will use xTB gfn2 and the
        alpb solvent model for water.
    ncores: int (optional)
        The number of cores to be used in the calculations. If set to None (default) will use
        the maximun number of available cores.
    maxcore: int (optional)
        For the engines that supprots it, the memory assigned to each core used in the
        computation.

    Returns
    -------
    float
        pKa of the molecule.
    System
        the structure of the considered deprotomer.
    """

    if method_opt is None:
        method_opt = XtbInput(solvent="water")

    method_opt.opt(protonated, inplace=True, ncores=ncores, maxcore=maxcore)

    if method_vib == method_el:
        method_el.freq(protonated, inplace=True, ncores=ncores, maxcore=maxcore)
    else:
        method_el.spe(protonated, inplace=True, ncores=ncores, maxcore=maxcore)

        if method_vib is not None and method_vib != method_opt:
            dummy = method_vib.freq(protonated, ncores=ncores, maxcore=maxcore)
            protonated.properties.set_vibronic_energy(
                dummy.properties.vibronic_energy, method_vib
            )

    deprotomers = deprotonate(
        protonated, ncores=ncores, maxcore=maxcore, solvent="water"
    )
    ordered_deprotomers = reorder_energies(
        deprotomers.systems,
        ncores=ncores,
        maxcore=maxcore,
        method_opt=method_opt,
        method_el=method_el,
        method_vib=method_vib,
    )

    lowest_deprotomer = ordered_deprotomers[0]

    pka = calculate_pka(protonated, lowest_deprotomer)

    return pka, lowest_deprotomer
