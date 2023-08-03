---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

(Guide-run)=
# Running calculations

After creating a `System`, and having initialized an `engine` or imported a `wrapper` function, we can actually start running calculations.

---

## Generic calculations (engines)

Generic calculations are implemented as class methods in the various `engines`. The available options, the class method name, and the engines for which they have been implemented are:

|  Calculation type  |  method name  |  Engines implemented  |
|  :---  |  :---  |  :---  |
|  Single point energy  |  `spe`  |  xTB, Orca, DFTB+  |
|  Geometry optimisation + Frequency analysis  |  `opt`  |  xTB, Orca, DFTB+  |
|  Frequency analysis  |  `freq` |  xTB, Orca  |
|  Numerical frequency analysis  |  `nfreq` |  Orca  |
|  Relaxed surface scan  |  `scan` |  Orca  |
|  Transition state optimization  |  `opt_ts` |  Orca  |
|  Transition state search via relaxed surface scan  |  `scan_ts` |  Orca  |
|  Climbing Image Nudged Elastic Band method  |  `neb_ci` |  Orca  |
|  Transition state search via Nudged Elastic Band method  |  `neb_ts` |  Orca  |
|  NVT Molecular Dynamics  |  `md_nvt` |  DFTB+  |
|  Simulated annealing  |  `simulated_annealing` |  DFTB+  |

---

The only mandatory parameter to be passed is the `System` on which to run the calculation. To run the calculation, simply call the function. The output of a calculation is (usually) a `System` object which can be assigned to a new variable:

```python
from spycci.systems import System
from spycci.engines.xtb import XtbInput

mol = System("water.xyz")
xtb = XtbInput()

mol_opt = xtb.opt(mol)

print(" ~~~ mol: ~~~")
print(mol)
print(" ~~~ mol_opt: ~~~")
print(mol_opt)
```

```{code-cell} python
:tags: ["remove-input"]
from spycci.systems import System

mol = System("../example_files/water.xyz")
mol_opt = System("../example_files/water.json")

print(" ~~~ mol: ~~~ ")
print(mol)
print(" ~~~ mol_opt: ~~~ ")
print(mol_opt)
```

Alternatively, you can directly update the input `System` with the `inplace` flag:

```python
from spycci.systems import System
from spycci.engines.xtb import XtbInput

mol = System("water.xyz")
xtb = XtbInput()

print(" ~~~ mol before opt: ~~~ ")
print(mol)

xtb.opt(mol, inplace=True)

print(" ~~~ mol after opt: ~~~ ")
print(mol)
```

```{code-cell} python
:tags: ["remove-input"]
from spycci.systems import System
from spycci.engines.xtb import XtbInput

mol1 = System("../example_files/water.xyz")
mol2 = System("../example_files/water.json")

print(" ~~~ mol before opt: ~~~ ")
print(mol1)
print(" ~~~ mol after opt: ~~~ ")
print(mol2)
```

---

## Special calculations (wrappers)

Some calculations are instead implemented as functions within the corresponding `wrapper` submodule, and work a little differently from the previous methods in the sense that they do not compute `System` properties but they usually generate other `System` objects (or collections thereof). While `Engines` are general-purpose tools which in theory allow the user to carry out similar calculations with different programs (e.g., geometry optimization via the `opt` function in `OrcaInput` or `XtbInput` are carried out in the same way), `wrappers` are much more program-specific and each wrapper allows to carry out different operations.

### CREST

|  Calculation type  |  method name  | 
|  :---  |  :---  | 
|  Tautomer search  |  `tautomer_search`  | 
|  Conformer search  |  `conformer_search`  |
|  Deprotomer search  |  `deprotonate` |
|  Protomer search  |  `protonate` | 
|  Quantum Cluster Growth  |  `qcg_grow` |
|  Quantum Cluster Growth + ensemble evaluation  |  `qcg_ensemble` |


These can be imported directly from the corresponding submodule. For more details on each specific function, please refer to the corresponding [API](API-wrappers-crest) page.

The CREST tautomer, conformer, deprotonation, and protonation routines all require a `System` object as input, and return a list of tautomer, conformers, deprotomers, and protomers, respectively, ordered by relative energy:

```python
from spycci.systems import System
from spycci.wrappers.crest import conformer_search

mol = System("mymol.xyz")
conformers = conformer_search(mol)

lowest_energy_conformer = conformers[0]
```

The QCG routines are used to create an explicitly solvated cluster, surrounding a solute with a certain number of solvent molecules. By default, the program keeps adding solvent molecules until energy convergence is reached with respect to the addition of other molecules. For more details on how to customise this kind of calculation, please refer to the [API](API-wrappers-crest) page.

```python
from spycci.systems import System
from spycci.wrappers.crest import qcg_grow

solute = System("solute.xyz")
solvent = System("solvent.xyz")

cluster = qcg_grow(solute, solvent)
```

### Packmol

The Packmol wrapper allows for the construction of explicitly solvated systems, as a fast alternative to the QCG routines, useful for setting up MD calculations. The currently available functions are:

|  Calculation type  |  method name  | 
|  :---  |  :---  | 
|  Generation of explicit solvation cube  |  `packmol_cube`  | 

Like the QCG routines, you need to provide a solute and a solvent `System`. The `packmol_cube` routine however allows you a finer degree of control, as you also need to provide two of the following three parameters:

  * `nsolv`: number of solvent molecules to put in the cube
  * `target_dens`: target density of the solvated box, in g/L
  * `cube_side`: length of the simulation box, in Å

Given two of these parameters, the third will be calculated accordingly. For example, the following code generates a cubic solvation box with 50 solvent molecules and a target density of 997 g/L:

```python
from spycci.systems import System
from spycci.wrappers.packmol import packmol_cube

solute = System("urea.xyz")
solvent = System("water.xyz")

solvated_cube = packmol_cube(solute, solvent, nsolv=50, target_dens=997)
print(solvated_cube)
```

```{code-cell} python
:tags: ["remove-input"]
from spycci.systems import System

solvated_cube = System("../example_files/solvated_cube.json")
print(solvated_cube)
```
