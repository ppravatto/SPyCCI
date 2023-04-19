import os, copy, shutil, sh, logging
import numpy as np
from typing import Dict, Optional
from tempfile import mkdtemp

import compechem.config as cfg
from compechem.config import get_ncores
from compechem.systems import Ensemble, System
from compechem.tools import process_output
from compechem.core.base import Engine
from compechem.core.dependency_finder import locate_orca
from compechem.core.spectroscopy import VibrationalData
from compechem.tools.internaltools import clean_suffix


logger = logging.getLogger(__name__)


class OrcaJobInfo:
    def __init__(self) -> None:
        self.__ncores: int = get_ncores()
        self.__maxcore: int = 750
        self.opt: bool = False
        self.freq: bool = False
        self.nfreq: bool = False
        self.scan: Optional[str] = None

        self.constraints: Optional[str] = None
        self.invert_constraints: bool = False

        self.cube_dim: Optional[int] = None

        self.hirshfeld: bool = False
        self.nearir: bool = False
        self.raman: bool = False

        self.__print_level: Optional[str] = None
        self.__optimization_level: Optional[str] = None
        self.__scf_convergence_level: Optional[str] = None
        self.__scf_convergence_strategy: Optional[str] = None
    
    @property
    def ncores(self) -> int:
        return self.__ncores
    
    @ncores.setter
    def ncores(self, value: Optional[int]) -> None:
        self.__ncores = get_ncores() if value is None else value

    @property
    def maxcore(self) -> int:
        return self.__maxcore
    
    @maxcore.setter
    def maxcore(self, value: Optional[int]) -> None:
        self.__maxcore = 750 if value is None else value

    @property
    def print_level(self) -> Optional[str]:
        return self.__print_level

    @print_level.setter
    def print_level(self, value: Optional[str]) -> None:
        if value is not None:
            ACCEPTED_VALUES = [
                "MINIPRINT",
                "SMALLPRINT",
                "NORMALPRINT",
                "LARGEPRINT",
            ]
            if value.upper() not in ACCEPTED_VALUES:
                raise ValueError(
                    f"`{value}` is not a valid optimization level. Must be one of {', '.join(ACCEPTED_VALUES)}"
                )

            self.__print_level = value.upper()

        else:
            self.__print_level = None

    @property
    def optimization_level(self) -> Optional[str]:
        return self.__optimization_level

    @optimization_level.setter
    def optimization_level(self, value: str) -> None:
        if value is not None:
            ACCEPTED_VALUES = [
                "VERYTIGHTOPT",
                "TIGHTOPT",
                "NORMALOPT",
                "LOOSEOPT",
            ]
            if value.upper() not in ACCEPTED_VALUES:
                raise ValueError(
                    f"`{value}` is not a valid optimization level. Must be one of {', '.join(ACCEPTED_VALUES)}"
                )

            self.__optimization_level = value.upper()

        else:
            self.__print_level = None

    @property
    def scf_convergence_level(self) -> Optional[str]:
        return self.__scf_convergence_level

    @scf_convergence_level.setter
    def scf_convergence_level(self, value: str) -> None:
        if value is not None:
            ACCEPTED_VALUES = [
                "NORMALSCF",
                "LOOSESCF",
                "SLOPPYSCF",
                "STRONGSCF",
                "TIGHTSCF",
                "VERYTIGHTSCF",
                "EXTREMESCF",
            ]
            if value.upper() not in ACCEPTED_VALUES:
                raise ValueError(
                    f"`{value}` is not a valid SCF convergence level. Must be one of {', '.join(ACCEPTED_VALUES)}"
                )

            self.__scf_convergence_level = value.upper()

        else:
            self.__print_level = None

    @property
    def scf_convergence_strategy(self) -> Optional[str]:
        return self.__scf_convergence_strategy

    @scf_convergence_strategy.setter
    def scf_convergence_strategy(self, value: str) -> None:
        if value is not None:
            ACCEPTED_VALUES = [
                "EASYCONV",
                "NORMALCONV",
                "SLOWCONV",
                "VERYSLOWCONV",
                "FORCECONV",
                "IGNORECONV",
            ]
            if value.upper() not in ACCEPTED_VALUES:
                raise ValueError(
                    f"`{value}` is not a valid convergence strategy. Must be one of {', '.join(ACCEPTED_VALUES)}"
                )

            self.__scf_convergence_strategy = value.upper()

        else:
            self.__print_level = None


class OrcaInput(Engine):
    """Interface for running Orca calculations.

    Parameters
    ----------
    method : str
        level of theory, by default "PBE"
    basis_set : str, optional
        basis set, by default "def2-TZVP"
    aux_basis : str, optional
        auxiliary basis set for RIJCOSX, by default "def2/J"
    solvent : str, optional
        SMD solvent, by default None
    optionals : str, optional
        optional keywords, by default ""
    scf_block: Dict[str, str], optional
        the dictionary containing the key and values to be added under the `%scf` block
    ORCADIR: str, optional
        the path or environment variable containing the path to the ORCA folder. If set
        to None (default) the orca executable will be loaded automatically.
    """

    def __init__(
        self,
        method: str = "PBE",
        basis_set: str = "def2-TZVP",
        aux_basis: str = "def2/J",
        solvent: str = None,
        optionals: str = "",
        scf_block: Dict[str, str] = {},
        ORCADIR: str = None,
    ) -> None:
        super().__init__(method)

        self.basis_set = basis_set if basis_set else ""
        self.aux_basis = aux_basis if aux_basis else ""
        self.solvent = solvent
        self.optionals = optionals
        self.scf_block = scf_block
        self.__ORCADIR = ORCADIR if ORCADIR else locate_orca(get_folder=True)

        self.level_of_theory += f""" | basis: {basis_set} | solvent: {solvent}"""

        self.__output_suffix = f"orca_{method}"
        self.__output_suffix += f"_{basis_set}" if basis_set else ""
        self.__output_suffix += f"_{solvent}" if solvent else "_vacuum"
        self.__output_suffix = clean_suffix(self.__output_suffix)

    def write_input(
        self,
        mol: System,
        job_info: OrcaJobInfo,
    ) -> None:
        
        mol.geometry.write_xyz(f"{mol.name}.xyz")

        logger.debug(f"Running ORCA calculation on {job_info.ncores} cores and {job_info.maxcore} MB of RAM")

        input = (
            "%pal\n"
            f"  nprocs {job_info.ncores}\n"
            "end\n\n"
            f"%maxcore {job_info.maxcore}\n\n"
            f"! {self.method} {self.basis_set} {self.optionals}\n"
        )

        if job_info.scf_convergence_strategy is not None or job_info.scf_convergence_level is not None:
            input += "! "

            if job_info.scf_convergence_level is not None:
                input += job_info.scf_convergence_level
                input += ""

            if job_info.scf_convergence_strategy is not None:
                input += job_info.scf_convergence_strategy
                input += " "
            input += "\n"

        if self.aux_basis:
            input += f"! RIJCOSX {self.aux_basis}\n\n"
        
        if job_info.print_level is not None:
            input += f"! {job_info.print_level}\n\n"

        if job_info.opt is True and job_info.freq is True and self.solvent is not None:
            logger.warning("Optimization with frequency in solvent was requested. Switching to numerical frequencies.")
            job_info.freq = False
            job_info.nfreq = True

        if job_info.opt is True:
            input += "! Opt\n" if job_info.optimization_level is None else f"! {job_info.optimization_level}\n"

        if job_info.freq is True:
            if self.solvent:
                logger.warning("Analytical frequencies are not supported for the SMD solvent model.")

            input += "! Freq\n"

        if job_info.nfreq is True:
            input += "! NumFreq\n"

        if job_info.nearir is True:
            input += "! NearIR\n"       

        if job_info.scan is not None:

            input += "! Opt\n"
            input += "%geom\n" "  scan\n" f"    {job_info.scan}\n" "  end\n"
            if job_info.constraints is not None:
                input += "  constraints\n" f"    {{ {job_info.constraints} C }}\n" "  end\n"
            if job_info.invert_constraints is True:
                input += "  invertConstraints true\n"
            input += "end\n\n"

        if self.solvent:
            input += "%CPCM\n" "  SMD True\n" f'  SMDsolvent "{self.solvent}"\n' "end\n\n"

        if job_info.cube_dim is not None:
            input += "%plots\n"
            input += "  Format Gaussian_Cube\n"
            input += f"  dim1 {job_info.cube_dim}\n"
            input += f"  dim2 {job_info.cube_dim}\n"
            input += f"  dim3 {job_info.cube_dim}\n"
            input += '  ElDens("eldens.cube");\n'
            if mol.spin != 1:
                input += '  SpinDens("spindens.cube");\n'
            input += "end\n\n"

        if job_info.hirshfeld is True:
            input += "%output\n"
            input += "  Print[P_Hirshfeld] 1\n"
            input += "end\n\n"

        if self.scf_block != {}:
            input += "%scf\n"
            for key, value in self.scf_block.items():
                input += f"  {key} {value}\n"
            input += "end\n\n"

        if job_info.raman is True:
            input += "%elprop\n"
            input += "  Polar 1\n"
            input += "end\n\n"

        input += f"* xyzfile {mol.charge} {mol.spin} {mol.name}.xyz\n"

        with open("input.inp", "w") as inp:
            inp.writelines(input)

        return

    def spe(
        self,
        mol: System,
        ncores: int = None,
        maxcore: int = 750,
        save_cubes: bool = False,
        cube_dim: int = 250,
        hirshfeld: bool = False,
        inplace: bool = False,
        remove_tdir: bool = True,
    ):
        """Single point energy calculation.

        Parameters
        ----------
        mol : System object
            input molecule to use in the calculation
        ncores : int, optional
            number of cores, by default all available cores
        maxcore : int, optional
            memory per core, in MB, by default 750
        save_cubes: bool, optional
            if set to True, will save a cube file containing electronic and spin densities,
            by default False.
        cube_dim: int, optional
            resolution for the cube files (default 250)
        hirshfeld: bool
            if set to true, will run the Hirshfeld population analysis. (default: False)
        inplace : bool, optional
            updates info for the input molecule instead of outputting a new molecule object,
            by default False
        remove_tdir : bool, optional
            temporary work directory will be removed, by default True

        Returns
        -------
        newmol : System object
            Output molecule containing the new energies.
        """

        logger.info(f"{mol.name}, charge {mol.charge} spin {mol.spin} - {self.method} SPE")

        tdir = mkdtemp(
            prefix=mol.name + "_",
            suffix=f"_{self.__output_suffix}_spe",
            dir=os.getcwd(),
        )

        with sh.pushd(tdir):
            job_info = OrcaJobInfo()
            job_info.ncores = ncores
            job_info.maxcore = maxcore
            job_info.cube_dim = None if save_cubes is False else cube_dim
            job_info.hirshfeld = hirshfeld

            self.write_input(mol=mol, job_info=job_info)

            cmd = f"{self.__ORCADIR}/orca input.inp > output.out '{cfg.MPI_FLAGS}'"
            logger.debug(f"Running Orca with command: {cmd}")
            os.system(cmd)

            if inplace is False:
                newmol = System(f"{mol.name}.xyz", charge=mol.charge, spin=mol.spin)
                newmol.properties = copy.copy(mol.properties)
                self.parse_output(newmol)

            else:
                self.parse_output(mol)

            process_output(mol, self.__output_suffix, "spe", mol.charge, mol.spin, save_cubes=save_cubes)

            if remove_tdir:
                shutil.rmtree(tdir)

            if inplace is False:
                return newmol

    def opt(
        self,
        mol: System,
        ncores: int = None,
        maxcore: int = 750,
        save_cubes: bool = False,
        cube_dim: int = 250,
        hirshfeld: bool = False,
        inplace: bool = False,
        remove_tdir: bool = True,
        optimization_level: Optional[str] = None,
        frequency_analysis: bool = True,
    ):
        """Geometry optimization + frequency analysis.

        Parameters
        ----------
        mol : System object
            input molecule to use in the calculation
        ncores : int, optional
            number of cores, by default all available cores
        maxcore : int, optional
            memory per core, in MB, by default 750
        save_cubes: bool, optional
            if set to True, will save a cube file containing electronic and spin densities,
            by default False.
        cube_dim: int, optional
            resolution for the cube files (default 250)
        hirshfeld: bool
            if set to true, will run the Hirshfeld population analysis. (default: False)
        inplace : bool, optional
            updates info for the input molecule instead of outputting a new molecule object,
            by default False
        remove_tdir : bool, optional
            temporary work directory will be removed, by default True
        optimization_level: str
            The convergence level to be adopted during the geometry optimization (Default: NORMALOPT)
        frequency_analysis: bool
            If set to True (default) will also compute the vibration modes of the molecule and the frequencies. If the
            optimization is run in solvent, it will automatically switch to numerical frequencies.

        Returns
        -------
        newmol : System object
            Output molecule containing the new geometry and energies.
        """

        logger.info(f"{mol.name}, charge {mol.charge} spin {mol.spin} - {self.method} OPT")

        tdir = mkdtemp(
            prefix=mol.name + "_",
            suffix=f"_{self.__output_suffix}_opt",
            dir=os.getcwd(),
        )

        with sh.pushd(tdir):
            job_info = OrcaJobInfo()
            job_info.ncores = ncores
            job_info.maxcore = maxcore
            job_info.opt = True
            job_info.freq = frequency_analysis
            job_info.cube_dim = cube_dim
            job_info.hirshfeld = hirshfeld
            job_info.optimization_level = optimization_level

            self.write_input(mol=mol, job_info=job_info)

            cmd = f"{self.__ORCADIR}/orca input.inp > output.out '{cfg.MPI_FLAGS}'"
            logger.debug(f"Running Orca with command: {cmd}")
            os.system(cmd)

            if inplace is False:
                newmol = System("input.xyz", charge=mol.charge, spin=mol.spin)
                newmol.name = mol.name
                newmol.geometry.level_of_theory_geometry = self.level_of_theory
                self.parse_output(newmol)

            else:
                mol.geometry.load_xyz("input.xyz")
                mol.geometry.level_of_theory_geometry = self.level_of_theory
                self.parse_output(mol)

            process_output(mol, self.__output_suffix, "opt", mol.charge, mol.spin, save_cubes=save_cubes)

            if remove_tdir:
                shutil.rmtree(tdir)

            if inplace is False:
                return newmol

    def freq(
        self,
        mol: System,
        ncores: int = None,
        maxcore: int = 750,
        inplace: bool = False,
        remove_tdir: bool = True,
        raman: bool = False,
        overtones: bool = False,
    ):
        """Frequency analysis (analytical frequencies).

        Note: if the SMD solvation model is detected, defaults to numerical frequencies
        (analytical frequencies are not currently supported)

        Parameters
        ----------
        mol : System object
            input molecule to use in the calculation
        ncores : int, optional
            number of cores, by default all available cores
        maxcore : int, optional
            memory per core, in MB, by default 750
        inplace : bool, optional
            updates info for the input molecule instead of outputting a new molecule object,
            by default False
        remove_tdir : bool, optional
            temporary work directory will be removed, by default True
        raman: bool
            If set to True will compute the Raman spectrum. (default: False)
        overtones: bool
            If set to True will enable the computation of infrared overtones and combination
            bands. (default: False)

        Returns
        -------
        newmol : System object
            Output molecule containing the new energies.
        """

        logger.info(f"{mol.name}, charge {mol.charge} spin {mol.spin} - {self.method} FREQ")

        tdir = mkdtemp(
            prefix=mol.name + "_",
            suffix=f"_{self.__output_suffix}_freq",
            dir=os.getcwd(),
        )

        with sh.pushd(tdir):
            job_info = OrcaJobInfo()
            job_info.ncores = ncores
            job_info.maxcore = maxcore
            job_info.freq = True
            job_info.raman = raman
            job_info.nearir = overtones

            self.write_input(mol=mol, job_info=job_info)

            cmd = f"{self.__ORCADIR}/orca input.inp > output.out '{cfg.MPI_FLAGS}'"
            logger.debug(f"Running Orca with command: {cmd}")
            os.system(cmd)

            if inplace is False:
                newmol = System(f"{mol.name}.xyz", charge=mol.charge, spin=mol.spin)
                newmol.properties = copy.copy(mol.properties)
                self.parse_output(newmol)

            else:
                self.parse_output(mol)

            process_output(mol, self.__output_suffix, "freq", mol.charge, mol.spin)

            if remove_tdir:
                shutil.rmtree(tdir)

            if inplace is False:
                return newmol

    def nfreq(
        self,
        mol: System,
        ncores: int = None,
        maxcore: int = 750,
        inplace: bool = False,
        remove_tdir: bool = True,
        raman: bool = False,
        overtones: bool = False,
    ):
        """Frequency analysis (numerical frequencies).

        Parameters
        ----------
        mol : System object
            input molecule to use in the calculation
        ncores : int, optional
            number of cores, by default all available cores
        maxcore : int, optional
            memory per core, in MB, by default 750
        inplace : bool, optional
            updates info for the input molecule instead of outputting a new molecule object,
            by default False
        remove_tdir : bool, optional
            temporary work directory will be removed, by default True
        raman: bool
            If set to True will compute the Raman spectrum.
        overtones: bool
            Is set to True will enable the computation of infrared overtones and combination
            bands.

        Returns
        -------
        newmol : System object
            Output molecule containing the new energies.
        """

        logger.info(f"{mol.name}, charge {mol.charge} spin {mol.spin} - {self.method} NFREQ")

        tdir = mkdtemp(
            prefix=mol.name + "_",
            suffix=f"_{self.__output_suffix}_nfreq",
            dir=os.getcwd(),
        )

        with sh.pushd(tdir):
            job_info = OrcaJobInfo()
            job_info.ncores = ncores
            job_info.maxcore = maxcore
            job_info.nfreq = True
            job_info.raman = raman
            job_info.nearir = overtones

            self.write_input(mol=mol, job_info=job_info)

            cmd = f"{self.__ORCADIR}/orca input.inp > output.out '{cfg.MPI_FLAGS}'"
            logger.debug(f"Running Orca with command: {cmd}")
            os.system(cmd)

            if inplace is False:
                newmol = System(f"{mol.name}.xyz", charge=mol.charge, spin=mol.spin)
                newmol.properties = copy.copy(mol.properties)
                self.parse_output(newmol)

            else:
                self.parse_output(mol)

            process_output(mol, self.__output_suffix, "numfreq", mol.charge, mol.spin)
            if remove_tdir:
                shutil.rmtree(tdir)

            if inplace is False:
                return newmol

    def scan(
        self,
        mol: System,
        scan: str = None,
        constraints: str = None,
        invertconstraints: bool = False,
        ncores: int = None,
        maxcore: int = 750,
        remove_tdir: bool = True,
    ):
        """Relaxed surface scan.

        Parameters
        ----------
        mol : System object
            input molecule to use in the calculation
        scan : str
            string for the scan section in the %geom block
        constraints : str
            string for the constraints section in the %geom block
        invertconstraints : bool, optional
            if True, treats the constraints block as the only coordinate NOT to constrain
        ncores : int, optional
            number of cores, by default all available cores
        maxcore : int, optional
            memory per core, in MB, by default 750
        remove_tdir : bool, optional
            temporary work directory will be removed, by default True

        Returns
        -------
        scan_list : Ensemble object
            Output Ensemble containing the scan frames.
        """

        logger.info(f"{mol.name}, charge {mol.charge} spin {mol.spin} - {self.method} SCAN")

        tdir = mkdtemp(
            prefix=mol.name + "_",
            suffix=f"_{self.__output_suffix}_scan",
            dir=os.getcwd(),
        )

        with sh.pushd(tdir):
            job_info = OrcaJobInfo()
            job_info.ncores = ncores
            job_info.maxcore = maxcore
            job_info.scan = scan
            job_info.constraints = constraints
            job_info.invert_constraints = invertconstraints

            self.write_input(mol=mol, job_info=job_info)

            cmd = f"{self.__ORCADIR}/orca input.inp > output.out '{cfg.MPI_FLAGS}'"
            logger.debug(f"Running Orca with command: {cmd}")
            os.system(cmd)

            xyz_list = [
                xyz
                for xyz in os.listdir(".")
                if os.path.splitext(xyz)[1] == ".xyz"
                and os.path.splitext(xyz)[0][:5] == "input"
                and xyz != "input.xyz"
                and xyz != "input_trj.xyz"
            ]

            mol_list = []

            # ---> evaluate if this section should/could be included in parse_output
            energies = []
            with open("output.out", "r") as f:
                read_energies = False
                for line in f:
                    if "The Calculated Surface using the SCF energy" in line:
                        read_energies = True
                        continue
                    if read_energies:
                        if len(line.split()) == 2:
                            energies.append(float(line.split()[-1]))
                        else:
                            break
            # <---

            for xyz in xyz_list:
                index = xyz.split(".")[1]
                shutil.move(f"input.{index}.xyz", f"{mol.name}.{index}.xyz")
                system = System(f"{mol.name}.{index}.xyz", charge=mol.charge, spin=mol.spin)
                system.properties.set_electronic_energy(energies.pop(0), self)
                mol_list.append(system)

            ensemble = Ensemble(mol_list)

            process_output(mol, self.__output_suffix, "scan", mol.charge, mol.spin)
            if remove_tdir:
                shutil.rmtree(tdir)

            return ensemble

    def parse_output(self, mol: System) -> None:
        """
        The function will parse an ORCA output file automatically looking for all the relevant
        numerical properties derived form a calculation. All the properties of the given molecule
        will be set or updated.

        Parameters
        ----------
        mol: System
            The System to which the properties must be written to.

        Raises
        ------
        RuntimeError
            Exception raised if the given path to the output file is not valid.
        """

        if not os.path.isfile("output.out"):
            raise RuntimeError("Cannot parse output, the `output.out` file does not exist.")

        normal_termination = False
        with open("output.out", "r") as outfile:
            for line in outfile:
                if "****ORCA TERMINATED NORMALLY****" in line:
                    normal_termination = True
                    break

        if normal_termination is False:
            logger.error("Error occurred during orca calculation.")
            raise RuntimeError("Error occurred during orca calculation")

        # Parse the final single point energy and the vibronic energy
        # -----------------------------------------------------------------------------------
        with open("output.out", "r") as out:
            for line in out:
                if "FINAL SINGLE POINT ENERGY" in line:
                    electronic_energy = float(line.split()[-1])
                    mol.properties.set_electronic_energy(electronic_energy, self)
                if "G-E(el)" in line:
                    vibronic_energy = float(line.split()[-4])
                    mol.properties.set_vibronic_energy(vibronic_energy, self)
                if "Final Gibbs free energy" in line:
                    gibbs_free_energy = float(line.split()[-2])
                    mol.properties.set_gibbs_free_energy(gibbs_free_energy, self, self)

        # Parse the Mulliken atomic charges and spin populations
        # -----------------------------------------------------------------------------------
        counter = 0
        mulliken_charges, mulliken_spins = [], []
        spin_available = False
        with open("output.out", "r") as file:
            # Count the number of "MULLIKEN ATOMIC CHARGES" sections in the file
            sections = file.read().count("MULLIKEN ATOMIC CHARGES")

            # Trace back to the beginning of the file
            file.seek(0)

            # Cycle over all the lines of the fuke
            for line in file:
                # If a "MULLIKEN ATOMIC CHARGES" section is found, increment the counter
                if "MULLIKEN ATOMIC CHARGES" in line:
                    counter += 1

                # If the index of the "MULLIKEN ATOMIC CHARGES" correspond with the last one
                # proceed with the file parsing else continue
                if counter == sections:
                    # Check if the section contains also the "SPIN" column (either "SPIN POPULATIONS" or "SPIN DENSITIES")
                    if "SPIN" in line:
                        spin_available = True

                    _ = file.readline()  # Skip the table line

                    # Iterate over the whole section reading line by line
                    while True:
                        buffer = file.readline()
                        if "Sum of atomic charges" in buffer:
                            break
                        else:
                            data = buffer.replace(":", "").split()
                            mulliken_charges.append(float(data[2]))

                            if spin_available:
                                mulliken_spins.append(float(data[3]))
                            else:
                                mulliken_spins.append(0.0)
                else:
                    continue

                # If break has been called after mulliken has been modified the section end
                # has been reached, as such, break also from the reading operation
                if mulliken_charges != []:
                    break

        if mulliken_charges != []:
            mol.properties.set_mulliken_charges(mulliken_charges, self)
            mol.properties.set_mulliken_spin_populations(mulliken_spins, self)

        # Parse the Hirshfeld atomic charges and spin populations
        # -----------------------------------------------------------------------------------
        hirshfeld_charges, hirshfeld_spins = [], []
        with open("output.out", "r") as file:
            for line in file:
                # Read the file until the HIRSHFELD ANALYSIS title is found
                if "HIRSHFELD ANALYSIS" in line:
                    # Discard the following 6 lines to skip formatting and total integrated
                    # densities
                    for i in range(6):
                        _ = file.readline()

                    # Read the whole hirshfeld section until a empty line is found
                    while True:
                        # Read the next line
                        buffer = file.readline()

                        # If the line is empty then break else parse the line
                        if buffer == "\n":
                            break

                        else:
                            data = buffer.split()
                            hirshfeld_charges.append(float(data[2]))
                            hirshfeld_spins.append(float(data[3]))

                elif hirshfeld_charges != []:
                    break

        if hirshfeld_charges != []:
            mol.properties.set_hirshfeld_charges(hirshfeld_charges, self)
            mol.properties.set_hirshfeld_spin_populations(hirshfeld_spins, self)

        # If available parse the section related to the vibrational analysis
        # -----------------------------------------------------------------------------------
        with open("output.out", "r") as file:
            vibrational_data = None

            for line in file:
                if "VIBRATIONAL FREQUENCIES" in line:
                    vibrational_data = VibrationalData()

                    # Discard the following 4 lines to skip formatting
                    for i in range(4):
                        _ = file.readline()

                    # Read the whole vibrational frequencies section
                    while True:
                        # Read the line
                        buffer = file.readline()

                        # Break if the line is empty
                        if buffer == "\n":
                            break

                        # Parse the frequency line and append it to the vibrational_data class
                        frequency = float(buffer.split(":")[-1].rstrip("cm**-1\n"))
                        vibrational_data.frequencies.append(frequency)

                elif "NORMAL MODES" in line:
                    # Discard the following 6 lines to skip formatting
                    for i in range(6):
                        _ = file.readline()

                    block = 0
                    while True:
                        # Discard the header line of the table block
                        _ = file.readline()

                        # Read the data within the current table block
                        ncoords = 3 * mol.geometry.atomcount
                        modes_left = ncoords - 6 * block

                        # If all the blocks have been already readed, break
                        if modes_left <= 0:
                            break

                        # Compute the number of data columns in the block
                        ncols = 6 if modes_left > 6 else modes_left

                        # Read each vector line by line
                        modes_buffer = [[] for i in range(ncols)]
                        for _ in range(ncoords):
                            sline = file.readline().split()

                            for i, element in enumerate(sline[1::]):
                                modes_buffer[i].append(float(element))

                        # Add all the obtained vectors to the vibrational data class
                        for vector in modes_buffer:
                            vibrational_data.normal_modes.append(np.array(vector))

                        # Increment the block counter
                        block += 1

                elif "IR SPECTRUM" in line:
                    # Discard the following 5 lines to skip formatting
                    for i in range(5):
                        _ = file.readline()

                    while True:
                        # Read the table line by line
                        line = file.readline()

                        # Check if the end of the table has been reached
                        if line == "\n":
                            break

                        # Split the mode index field from the rest of the data
                        sline = line.split(":")

                        # Add the mode index and the transition intensity in km/mol
                        vibrational_data.ir_transitions.append((int(sline[0]), float(sline[1].split()[2])))

                elif "OVERTONES AND COMBINATION BANDS" in line:
                    # Discard the following 5 lines to skip formatting
                    for i in range(5):
                        _ = file.readline()

                    while True:
                        # Read the table line by line
                        line = file.readline()

                        # Check if the end of the table has been reached
                        if line == "\n":
                            break

                        # Split the mode index field from the rest of the data
                        sline = line.split(":")

                        mode_index = [int(x) for x in sline[0].split("+")]
                        transition_intensity = float(sline[1].split()[2])

                        # Add the modes indeces and the transition intensity in km/mol
                        vibrational_data.ir_combination_bands.append(
                            (mode_index[0], mode_index[1], transition_intensity)
                        )

                elif "RAMAN SPECTRUM" in line:
                    # Discard the following 4 lines to skip formatting
                    for i in range(4):
                        _ = file.readline()

                    while True:
                        # Read the table line by line
                        line = file.readline()

                        # Check if the end of the table has been reached
                        if line == "\n":
                            break

                        # Split the mode index field from the rest of the data
                        sline = line.split(":")
                        mode_index = int(sline[0])
                        activity = float(sline[1].split()[1])
                        depolarization = float(sline[1].split()[2])

                        # Add the mode index, activity and depolarization
                        vibrational_data.raman_transitions.append((mode_index, activity, depolarization))

            if vibrational_data is not None:
                mol.properties.set_vibrational_data(vibrational_data, self)

    @property
    def output_suffix(self) -> str:
        """
        Suffix used to compose the name of calculation output files

        Returns
        -------
        str
            The output suffix string
        """
        return self.__output_suffix


class M06(OrcaInput):
    def __init__(self):
        super().__init__(
            method="M062X",
            basis_set="def2-TZVP",
            aux_basis="def2/J",
            solvent="water",
            optionals="DEFGRID3",
        )


class r2SCAN(OrcaInput):
    def __init__(self):
        super().__init__(
            method="r2SCAN-3c",
            basis_set="",
            aux_basis=None,
            solvent="water",
            optionals="",
        )


class CCSD(OrcaInput):
    def __init__(self):
        super().__init__(
            method="DLPNO-CCSD",
            basis_set="Extrapolate(2/3,ANO)",
            aux_basis="AutoAux",
            solvent="water",
            optionals="",
        )
