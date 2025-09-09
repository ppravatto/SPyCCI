(Guide-setup)=
# Setting up calculations

After creating a `System` object, encoding the molecular geometry, you need to set up the calculation to which you wish to subject it. This is done with the `spycci.engines` and `spycci.wrappers` submodules.

Both `engines` and `wrappers` submodules contains a series of program-specific classes and functions for interfacing with external code and carrying out calculations on `System` objects. The distinction between the two and the philosophy behind them is as follows:

* an `engine` carries out calculations on a `System` for computing properties (e.g. geometry optimizations, single point energies, frequencies, etc.) and usually sets the `properties` of a system object based on a well defined level of theory for the electronic and/or vibrational part. 

* a `wrapper` carries out calculations on a `System` for obtaining other, "processed" `System` objects. For example, conformer/tautomer searches, building of solvation boxes, etc.

The programs currently implemented as `engines` are:
* [xTB](https://github.com/grimme-lab/xtb)
* [Orca](https://orcaforum.kofo.mpg.de/index.php?sid=3c6c78cae3dd0cfffa26a293953422e3)
* [DFTB+](https://dftbplus.org/)
<!-- * [NAMD](http://www.ks.uiuc.edu/Research/namd/) (coming soon!) -->

The programs currently implemented as `wrappers` are:
* [CREST](https://crest-lab.github.io/crest-docs/)
* [PackMol](https://m3g.github.io/packmol/)

:::{admonition} Note
:class: warning
To function with the library, the external programs need to be already installed and available to the system from command line. Please read the section about [third party software compatibility](third-party-software-compatibility) to have more info.
:::

## Calling an `Engine`

The general-purpose `engines` are implemented as class objects named `<Program>Input`, where `<Program>` is the name of the software (with an initial capital letter). Each engine lives in its own submodule, nested under the main `engines` module. To use an engine, you first import it from its submodule, then create an instance of the corresponding class:

```python
from spycci.engines.xtb import XtbInput
from spycci.engines.dftbplus import DFTBInput
from spycci.engines.orca import OrcaInput

xtb = XtbInput()
dftb = DFTBInput()
orca = OrcaInput()
```

If you do not specify anything, some default options are chosen automatically for level of theory, basis set, solvation, etc. Please refer to the [API](API-engines) section for a complete list of options and default values.

As an example, let us set up a calculation with Orca, using the B3LYP functional, with the def2-TZVP basis set and def2/J auxiliary basis set, using the SMD implicit solvation model for water, and including Grimme's D3BJ dispersion corrections:

```python
from spycci.engines.orca import OrcaInput

b3lyp = OrcaInput(
    method = "B3LYP",
    basis_set = "def2-TZVP",
    aux_basis = "def2/J",
    solvent = "water",
    optionals = "D3BJ",
)
```

## Calling a `Wrapper`

For `wrappers`, you just need to import the corresponding `wrapper` submodule or any of the specific functions you wish to use:

```python
from spycci.wrappers.crest import tautomer_search

mol = System.from_xyz("water.xyz")
tautomers_list = tautomer_search(mol)
```

Please refer to the [API](API-wrappers) section for a complete list of the available wrapper functions.