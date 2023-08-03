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

(getting-started)=

# Getting Started

The `SPyCCI` package can be installed by first downloading the repository from our [GitHub](https://github.com/hbar-team/SPyCCI) page and then installing via `pip`. 

:::{admonition} Note
:class: warning
We always recommend installing new Python packages in a clean Conda environment and avoid installing in the system Python distribution or in the base Conda environment! If you are unfamiliar with Conda, please refer to their [documentation](https://docs.anaconda.com/free/anaconda/install/index.html) for a guide on how to set up environments.
:::

```
git clone https://github.com/hbar-team/SPyCCI
cd SPyCCI
pip install .
```

The library can be imported in a Python script via the following syntax:

```python
import spycci
```

Alternatively, individual submodules, classes, and functions can be imported separately:

```python
from spycci import systems
from spycci.engines import dftbplus
from spycci.wrappers.packmol import packmol_cube
```

For a more detailed explanation of the available features in each submodule, please refer to their specific page in this [User Guide](user-guide).

---

## My first calculation

### Introduction

Let us go through the very basics of using the library. We are going to carry out a geometry optimisation on a water molecule. At the very least, you will need the geometrical structure of the system you want to study, in the form of a `.xyz` file. You can obtain it from available databases, or you can draw the structures yourself in programs such as [Avogadro](https://avogadro.cc/).

Below is the `water.xyz` file, containing the structure of the water molecule, which we will use in these examples:

```
3

O   0.000  -0.736   0.000  
H   1.442   0.368   0.000  
H  -1.442   0.368   0.000  
```

If you open the file in a molecular visualization software, you will notice the structure is distorted from the typical equilibrium geometry. We can then optimise the structure by utilising one of the wrappers implemented in `SPyCCI`. We will use [xTB](https://github.com/grimme-lab/xtb) in this example, due to its balance between accuracy and speed. The library needs the program to already be installed ([preferably via conda](https://xtb-docs.readthedocs.io/en/latest/setup.html#setup-and-installation)) and ready to go.

### Importing the library

Before starting, we need to create a Python script and import the necessary classes from the library. We need the `System` class to store the information about our water molecule, and the `XtbInput` class to define the simulation setup (Hamiltonian, parameters, solvation, etc.):

```python
from spycci.systems import System
from spycci import XtbInput  # Engines can also be imported directly from spycci 
```

### Creating the System object

After importing the necessary modules, we can create our molecule, by indicating the (relative, or complete) path where the `.xyz` file is located:

```python
water = System("example_files/water.xyz")
```

### Creating a XtbInput object

We can now set up a engine object using an instance of `XtbInput`. Most of these engines come with sensible default options for calculations on small organic molecules in vacuum. To see all the available options, please refer to the [engine](API-engines) section of the API documentation.

```python
xtb = XtbInput()
```

### Carrying out the calculation

We can now carry out the calculation. We want to do a geometry optimization on our water molecule, and we want the original information for the molecule to be updated after the calculation (`inplace` flag). The syntax for this calculation is as follows:

```python
xtb.opt(water, inplace=True)
```

### Printing the results

If you want to see the data currently stored in our `System` object, simply ask for it to be printed to screen:

```python
print(water)
```

```{code-cell} python
:tags: ["remove-input"]
from spycci.systems import System
water = System("./example_files/water.xyz")
print(water)
```

Et voilà! You have successfully carried out a geometry optimization for the water molecule using the `SPyCCI` library!

`````{admonition} Basic molecule visualization
:class: tip
The `SPyCCI` library also offers simple tools to visualize the structure of the molecules encoded by a `System` object. As an example, the distorted structure of the input molecule, loaded into the `water` object, can be visualized using the built in [`mogli`](https://github.com/sciapp/mogli) interface using the commands:

```python
from spycci.tools.moglitools import MogliViewer

viewer = MogliViewer(water)
viewer.show()
```

The output image, freely capable of rotating, will look something like this:

```{image} ./images/water.png
:alt: water.png
:width: 600px
:align: center
```
`````