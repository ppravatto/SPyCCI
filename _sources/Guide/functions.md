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

(Guide-functions)=
# Calculating properties

The `spycci.functions` submodule contains a series of methods to "manually" calculate some physical properties of the system under study. The user is expected to provide the exact intended states for the system(s) under study, as the functions will simply take the inputs and generate the output without carrying out any checks. For example, if the user calculates the pKa of a molecule in an unoptimised geometry, the resulting pKa will be that of the unoptimised geometry.

The `spycci.functions` functions can be imported via the following syntax:

```python
from spycci.functions import calculate_pka
```

:::{admonition} Empirical corrections
:class: warning
The functions to calculate pKa and reduction potentials take into account the self-energy of proton and electron for calculations carried out with GFN2-xTB:
* electron self energy = $111.75\, \mathrm{kcal/mol}$
* proton self energy = $164.22\, \mathrm{kcal/mol}$
:::

---

## pKa

The `spycci.functions.pka` submodule provides an interface for the computation of the pKa or a given species. The module is, at this time, composed by two functions:

* `calculate_pka`: Computes the pKa of a molecular system and its deprotomer. The user must provide both streucture in the form of `System` objects with an already defined electronic energy and possibly a vibronic one.
* `auto_calculate_pka`: Computes the pKa of a given molecule by automatically searching the lowest-energy deprotomer using CREST. Once the proper deprotomer has been identified the function take care of the geometry optimization of both structures, the calculation of electronic energies and frequencies.


:::{admonition} Note
:class: info
Both functions return the computed pKa value and set the pKa as a property (`system.properties.pka`) of the protonated system. The `auto_calculate_pka` also returns the deprotonated system.
:::

In general terms both functions calculate the pKa of a molecule $HA$ considering a reaction of the type:

$$
HA \rightarrow H^{+} + A^{-}
$$

The equilibrium constant of the reaction is calculated as 

$$
pK_{a} = \frac{G_{A^{-}} + G_{H^{+}} - G_{HA}}{2.303 \cdot RT}
$$

where $G_{A^{-}}$ and $G_{HA}$ are calculated summing the electronic + vibronic energies at the selected/provided level of theory, $G_{H^{+}} = -270.29 kcal/mol$, $R = 1.987 \cdot 10^{-3} kcal/(mol \cdot K)$ and $T = 298.15 K$.

### The `calculate_pka()` function:

The `calculate_pka` function takes as arguments the following elements:

* `protonated` (`System`): molecule in its protonated form
* `deprotonated` (`System`): molecule in its deprotonated form

Please notice how both the `protonated` and `deprotonated` molecules must already be optimized (in water) and must posses a valid electronic energy value. If the vibronic energy is provided, its contribution is taken into account during the calculation.

An example script that can be used to compute the pKa of a molecule is provided in what follows:

```python
from spycci.engines.xtb import XtbInput
from spycci.systems import System
from spycci.functions.pka import calculate_pka

protonated = System("protonated.xyz", charge=0, spin=1)
deprotonated = System("deprotonated.xyz", charge=-1, spin=1)

xtb = XtbInput(solvent="water")
xtb.opt(protonated, inplace=True)
xtb.opt(deprotonated, inplace=True)

pka = calculate_pka(protonated, deprotonated)
```

### The `auto_calculate_pka()` function:

The `auto_calculate_pka` function takes as main argument the protonated molecule structure (in the form of a `System` object). The molecule is sequentially deprotonated using the CREST deprotomer search routine until the lowest energy deprotomer is identified. Once the deprotomer search has been completed, the structure of both molecules is optimized using the specified level of theory and both electronic and vibronic energies are computed at the user defined level of theory. The routine takes as arguments the following elements:

* `protonated` (`System`): The protonated molecule for which the pKa must be computed.
* `method_el` (`Engine`): The computational engine to be used in the electronic level of theory calculations.
* `method_vib` (`Engine`):  The computational engine to be used in the vibronic level of theory calculations. (optional)
* `method_opt` (`Engine`): The computational engine to be used in the geometry optimization of the protonated molecule and its deprotomers. (optional)
* `ncores` (`int`): The number of cores to be used in the calculations. (optional)
* `maxcore` (`int`):  For the engines that supprots it, the memory assigned to each core used in the computation. (optional)

An example script that can be used to compute the pKa of a molecule is provided in what follows:

```python
from spycci.engines.xtb import XtbInput
from spycci.systems import System
from spycci.functions.pka import calculate_pka

protonated = System(f"protonated.xyz", charge=0, spin=1)
xtb = XtbInput(solvent="water")

pka, deprotonated = auto_calculate_pka(
    protonated,
    method_el=xtb,
    method_vib=xtb,
    method_opt=xtb,
)
```
Please notice how the optimized structure of the deprotonated system is also returned together with the pKa value.

---

## 1-el redox potential

Calculates the one-electron reduction potential of a molecule $MH_{n}$, considering a generic reaction of the type:

$$
MH_{n} \rightarrow M^{\cdot (n-1)-} + n\cdot H^{+} + e^{-}
$$

provided the following arguments:

* `oxidised` (`System`): molecule in its oxidised state
* `reduced` (`System`): molecule in its reduced state
* `pH` (`float`, default: `7.0`): pH at which the reduction potential is calculated

and returns the reduction potential of the molecule considering the provided states at the provided pH, including eventual PCET mechanisms, calculated as:

$$
E°_{MH_{n}/M^{\cdot(n-1)-}} = - \frac{G_{M^{\cdot(n-1)-}} - (G_{MH_{n}} + n \cdot G_{H^{+}}) }{F} - E°_{SHE} - n \cdot 0.059 \cdot pH 
$$

where $G_{M^{\cdot(n-1)-}}$ and $G_{MH_{n}}$ are calculated summing the electronic + vibronic energies at the selected level of theory, $G_{H^{+}} = -270.29 kcal/mol$, $F = 23.061 kcal/volt–gram-equivalent$, and $E_{SHE} = 4.28 V$.

## Fukui functions
The `spycci.functions.calculate_fukui` function calculates the Fukui functions $f^+(r)$, $f^-(r)$ and $f^0(r)$ associated with a given molecular geometry. The Fukui functions are computed according to the definitions:

$$
f^+(r) = \rho_{N+1}(r) - \rho_{N}(r)
$$

$$
f^-(r) = \rho_{N}(r) - \rho_{N-1}(r)
$$

$$
f^0(r) = \frac{1}{2} \left[\rho_{N+1}(r) - \rho_{N-1}(r)\right]
$$

Where, given a molecule with $N$ electrons, $\rho_{N}(r)$ represents its electronic density while $\rho_{N\pm1}(r)$ represents the electronic density of the molecule, in the same nuclear configuration, when one electron is either added ($+1$) or removed ($-1$).

The Fukui functions are both computed as volumetric quantities and saved in a [Gaussian Cube](http://paulbourke.net/dataformats/cube/) compatible format in the `output_density` folder and as condensed values saved in the `System` object `properties` attribute in the form of a dictionary. The condensed Fukui functions are computed by applying the $f^+$, $f^-$ and $f^0$ definitions replacing the charge density with either the Mulliken charges or the Hirshfeld charges (changing the sign accordingly given that a localized electronic density represents an accumulation of electrons hence of negative charge). Please notice how the Hirshfeld charges are supported only by the `OrcaInput` engine.

::::{important}
Please notice how the Fukui cubes contain the localized Mulliken-charge-based Fukui values in place of the atomic charges. This is explained in the first comment line of each cube file and, for sake of clarity, all the files are saved using the extension `.fukui.cube`.
::::

The function can be called with the following minimal arguments:
* `molecule` (`System`): The molecular structure to be used in the computation
* `engine` (`OrcaInput` or `XtbInput`): The engine defining the level of theory to be used in the calculation.

The function assumes that the molecule supports only singlet and doublet states and switches the spin multeplicity according to the number of electrons. If different spin states needs to be considered the `spins_states` option can be used to provide the spin multeplicity values as a list.

An example code snippet is provided in what follows:
```python
from spycci.systems import System
from spycci.engines.orca import OrcaInput
from spycci.functions.fukui import calculate_fukui

mol = System("./acetaldehyde.xyz")
orca = OrcaInput(method="PBE", basis_set="def2-SVP")

orca.opt(mol, inplace=True)
calculate_fukui(mol, orca)

print(mol)
```

That for the acetaldehyde molecule returns the following result:

```{code-cell} python
:tags: ["remove-input"]
from spycci.systems import System
mol = System("../example_files/acetaldehyde.json")
print(mol)
```

The volumetric fukui functions can then be plotted using the built in `vmd` based rendering tool. As an example the following code can be used to render the the $f^+(r)$ Fukui function.

```python
from spycci.tools.vmdtools import render_fukui_cube

render_fukui_cube(
    "./output_densities/acetaldehyde_Fukui_plus.fukui.cube",
    include_negative=True,
    isovalue=0.02,
)
```

The rendered volume is saved in a `.bmp` bitmap image format. In the case of the acetaldehyde molecule considered in the example, the following image is obtained:

```{image} ../images/acetaldehyde_fukui_plus.bmp
:alt: fukui_plus
:class: bg-primary mb-1
:width: 600px
:align: center
```
