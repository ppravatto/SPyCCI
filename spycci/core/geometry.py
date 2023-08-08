from __future__ import annotations

import numpy as np

from os.path import isfile
from typing import Tuple, List, Union
from morfeus import BuriedVolume

from spycci.constants import atoms_dict, atomic_masses


class MolecularGeometry:
    """
    The `MolecularGeometry` class implements all the functions required to operate on the
    geometric properties of a given molecule or molecular aggregate.

    Attributes
    ----------
    level_of_theory_geometry: str
        The level of theory at which the geometry has been obtained.
    """

    def __init__(self) -> None:
        self.__atomcount: int = 0
        self.__atoms: List[str] = []
        self.__coordinates: List[np.ndarray] = []
        self.level_of_theory_geometry: str = None

    def __getitem__(self, index: int) -> Tuple[str, np.ndarray]:
        if index < 0 or index >= self.atomcount:
            raise ValueError(
                f"The index {index} is not valid (atomcount: {self.atomcount})"
            )
        return self.__atoms[index], self.__coordinates[index]

    def __iter__(self) -> Tuple[str, np.ndarray]:
        for atom, coordinates in zip(self.__atoms, self.__coordinates):
            yield atom, coordinates

    def __len__(self) -> int:
        return self.__atomcount

    def append(self, atom: str, coordinates: Union[List[float], np.ndarray]) -> None:
        """
        The append function allows the user to add the position of a new atom belonging to
        the molecule.

        Arguments
        ---------
        atom: str
            The symbol of the atom
        coordinates: Union[List[float], np.ndarray]
            The list or numpy array of 3 floating point values indicating the cartesian
            position of the atom in the tridimensional space

        Raises
        ------
        ValueError
            Exception raised if the atom does not represent a valid element or if the coordinates
            vector does not match the requirements
        """

        if atom not in atoms_dict.values():
            raise ValueError(f"The symbol {atom} is not a valid element")

        if len(coordinates) != 3:
            raise RuntimeError(
                f"The coordinate vector must contain 3 floating poin coordinates"
            )

        self.__atomcount += 1
        self.__atoms.append(atom)
        self.__coordinates.append(np.array(coordinates))

    @classmethod
    def from_xyz(cls, path: str) -> MolecularGeometry:
        """
        The functions returns a fully initialized `MolecularGeometry` class containing the
        coordinates indicated in the `.xyz` file located in the indicated path.

        Arguments
        ---------
        path: str
            A string indicating the path to a valid `.xyz` file

        Returns
        -------
        MolecularGeometry
            The `MolecularGeometry` object containing the coordinates encoded in the `.xyz` file
        """
        obj = cls()
        obj.load_xyz(path)
        return obj

    @classmethod
    def from_dict(cls, data: dict) -> MolecularGeometry:
        """
        Construct a MolecularGeometry object from the data encoded in a dictionary.

        Arguments
        ---------
        data: dict
            The dictionary containing the class attributes

        Returns
        -------
        MolecularGeometry
            The fully initialized MolecularGeometry object
        """
        obj = cls()
        obj.__atomcount = data["Number of atoms"]
        obj.__atoms = data["Elements list"]
        obj.__coordinates = [np.array(v) for v in data["Coordinates"]]
        obj.level_of_theory_geometry = data["Level of theory geometry"]
        return obj

    def to_dict(self) -> dict:
        """
        Generates a dictionary representation of the class. The obtained dictionary can be
        saved and used to re-load the object using the built-in `from_dict` class method.

        Returns
        -------
        dict
            The dictionary listing, with human friendly names, the attributes of the class
        """
        data = {}
        data["Number of atoms"] = self.__atomcount
        data["Elements list"] = self.__atoms
        data["Coordinates"] = [list(v) for v in self.__coordinates]
        data["Level of theory geometry"] = self.level_of_theory_geometry
        return data

    def load_xyz(self, path: str) -> None:
        """
        Imports the coordinates of the molecule from a path pointing to a valid `.xyz` file

        Arguments
        ---------
        path: str
            The path to the `.xyz` from which the coordinates must be loaded

        Raises
        ------
        ValueError
            Exception raised if the path given does not point to a valid file
        RuntimeError
            Exception raised if an error occurs while loading the data from the file
        """

        # Clean all the variables
        self.__atomcount = 0
        self.__atoms = []
        self.__coordinates = []

        # Check if the given path points to a valid file
        if not isfile(path):
            raise ValueError(f"The path {path} does not point to a valid file.")

        # Open the file in read mode
        with open(path, "r") as file:

            # Read the whole file and count both the number of lines and terminal empty lines
            nlines, offset = 0, 0
            for line in file:
                nlines += 1

                if line == "\n":
                    offset += 1
                else:
                    offset = 0

            file.seek(0)

            # Extract the number of atoms from the first line and compute the beginning of
            # the last xyz coordinate block (required when operating on trajectories)
            self.__atomcount = int(file.readline())
            beginning = nlines - (self.__atomcount + offset + 2)

            file.seek(0)

            # Read the file line by line starting from the beginning
            line: str = ""
            for n, line in enumerate(file):

                # Split the line to seprate the various fields
                sline = line.split()

                # Discart all the lines before the last block and the comment line
                if n < beginning or n == beginning + 1:
                    continue

                # Check that the block begins with the expected atomcount to confirm
                elif n == beginning:
                    if len(sline) != 1 or int(sline[0]) != self.__atomcount:
                        raise RuntimeError(
                            "The beginning of the xyz block does not match the expected atomcount"
                        )
                    else:
                        continue

                # Discard all the trailing empty lines
                elif line == "\n":
                    continue

                # If the file contains atomic numbers instead of symbols convert them into
                # the latter, else directly read the symbol
                try:
                    atom = atoms_dict[int(sline[0])]
                except:
                    atom = sline[0]

                # Check that the element exists between the list of known elements
                if atom not in atoms_dict.values():
                    raise RuntimeError(f"The symbol {atom} is not a valid element")

                # Append the atom and its coordinates to the class member variables
                self.__atoms.append(atom)
                self.__coordinates.append(np.array([float(x) for x in sline[1:4]]))

            # Check that the lengths of the array match the number of atoms expected
            if (
                len(self.__atoms) != self.__atomcount
                or len(self.__coordinates) != self.__atomcount
            ):
                raise RuntimeError("Mismatch between the atom count and the loaded data")

    def write_xyz(self, path: str, comment: str = "") -> None:
        """
        Exports the coordinates to a `.xyz` file located at a given path

        Arguments
        ---------
        path: str
            A valid path in which the `.xyz` file must be saved
        comment: str
            An optional comment that can be saved in the `.xyz` file
        """
        with open(path, "w") as file:

            file.write(f"{self.__atomcount}\n")
            file.write(f"{comment}\n")

            for atom, position in zip(self.__atoms, self.__coordinates):
                file.write(atom)
                for xi in position:
                    file.write(f"\t{xi:.10f}")
                file.write("\n")

    @property
    def atomcount(self) -> int:
        """
        The number of atoms in the molecule

        Returns
        -------
        int
            The number of atoms in the molecule
        """
        return self.__atomcount

    @property
    def atoms(self) -> List[str]:
        """
        The list of atoms/elements in the molecule

        Returns
        -------
        List[str]
            The list of strings representing, in order, the symbols of the atoms in the molecule
        """
        return self.__atoms

    @property
    def atomic_numbers(self) -> List[int]:
        """
        The ordered list of the atomic numbers of each atom in the molecule

        Returns
        -------
        List[int]
            The list of integers atomic numbers associated with each atom in the molecule
        """

        ATOMIC_NUMBERS = {v: k for k, v in atoms_dict.items()}
        return [ATOMIC_NUMBERS[element] for element in self.atoms]

    @property
    def coordinates(self) -> List[np.ndarray]:
        """
        The list of coordinates of the atoms in the molecule

        Returns
        -------
        List[np.ndarray]
            The list of numpy arrays representing, in order, the 3D position of each atom
            in the molecule
        """
        return self.__coordinates

    @property
    def mass(self) -> float:
        """
        The mass of the molecule in atomic mass units computed using the average atomic weights.

        Returns
        -------
        float
            The molecular mass in atomic mass units.
        """
        mass = 0
        for atom in self.__atoms:
            mass += atomic_masses[atom]
        return mass
    
    @property
    def center_of_mass(self) -> np.ndarray:
        """
        The center of mass of the molecule as a vector from the cartesian system origin

        Returns
        -------
        np.ndarray
            An array encoding the position of the center of mass from the origin (0, 0, 0).
        """
        rcm = np.array([0., 0., 0.])
        for atom, r in self:
            rcm += atomic_masses[atom]*r

        return rcm/self.mass
    
    def translate(self, rcm: List[float] = [0., 0., 0.]) -> None:
        """
        Translate, (move without rotations), the molecule center of mass to a new user-specified location.

        Arguments
        ---------
        rcm: List[float]
            The 3D vector encoding the new position of the molecule center of mass.
        
        Raises
        ------
        ValueError
            Exception raised if the vector given by the user is invalid.
        """
        if len(rcm) != 3:
            raise ValueError("A three-dimensional vector is espected as the new position of the center of mass")
        
        delta = np.array(rcm) - self.center_of_mass
        self.__coordinates = [r + delta for r in self.__coordinates]

    def buried_volume_fraction(
        self,
        site: int,
        radius: float = 3.5,
        density: float = 0.001,
        include_hydrogens: bool = True,
        excluded_atoms: List[int] = None,
        radii: List[float] = None,
        radii_type: str = "bondi",
        radii_scale: float = 1.17,
    ):
        """
        Computes the buried volume fraction around a given site. The functions adopts the implementation
        provided in the morfeus python package (https://kjelljorner.github.io/morfeus/buried_volume.html).

        Arguments
        ---------
        site: int
            The index (starting the numeration from zero) of the reactive atom around which
            the buried volume must be computed
        radius: float
            The radius (in Angstrom) of the sphere in which the buried volume should be computed
        density: float
            The volume (in Angstrom^3) per point in the sphere used in the calculation
        include_hydrogens: bool
            If set to True (default) will consider the hydrogen atoms in the calculation
        excluded_atoms: List[int]
            The list of indices (starting the numeration from zero) of the atom that should be
            excluded from the compuitation of the buried volume (default: None)
        radii: List[float]
            The custom list of atomic radii to be used in the computation (default: None).
            If set to a value different from `None`, will override the `radii_type` and 
            `radii_scale` options.
        radii_type: str
            Type of radii to use in the calculation. The available options are `alvarez`,
            `bondi`, `crc` or `truhlar`.
        radii_scale: float
            Scaling factor for the selected radii_type
        
        Raises
        ------
        ValueError
            Exception raised if either the index of the selected atoms are out of bounds or
            if the radii type does not match any of the presets.
        
        Returns
        -------
        float
            The fraction of buried volume of the sphere (between 0 and 1)
        """

        if site < 0 or site >= self.atomcount:
            raise ValueError(
                f"The site index {site} is out of bounds (current atomcount: {self.atomcount})"
            )

        if excluded_atoms != None:
            for idx in excluded_atoms:
                if idx < 0 or idx >= self.atomcount:
                    raise ValueError(
                        f"The excluded atom index {idx} is out of bounds (current atomcount: {self.atomcount})"
                    )
        
        if radii_type not in ['alvarez', 'bondi', 'crc', 'truhlar']:
            raise ValueError(f"The radii definition {radii_type} is not available at this time.")

        if radii is not None:
            if len(radii) != self.atomcount:
                raise ValueError("The length of the radii list must match the number of atoms in the molecule")

        bv = BuriedVolume(
            self.atoms,
            self.coordinates,
            site + 1,
            excluded_atoms=[idx + 1 for idx in excluded_atoms] if excluded_atoms is not None else None,
            radii=radii,
            radii_type=radii_type,
            radii_scale=radii_scale,
            density=density,
            include_hs=include_hydrogens,
            radius=radius,
        )

        return bv.fraction_buried_volume
    