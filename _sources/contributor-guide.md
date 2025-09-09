# Contributor's guide

`SPyCCI` is an open source project and, as such, all the contributions are well accepted. If you want to contribute to the library, a simple guide on how to interface with the GitHub repository is provided in what follows.

## General development process

* If you are a first-time contributor:

    * Go to [https://github.com/hbar-team/SPyCCI](https://github.com/hbar-team/SPyCCI) and click the “fork” button to create your own copy of the project repository.

    * Clone the project to your local computer using the command (where `<YOUR_USERNAME>` represent your personal GitHub username): 
        ```
        git clone https://github.com/<YOUR_USERNAME>/SPyCCI
        ```

    * Enter the reposiotry directory using the command:
        ```
        cd SPyCCI
        ```

    * Add the upstream repository using the command:
        ```
        git remote add upstream https://github.com/hbar-team/SPyCCI.git
        ```

    * Now, when running the `git remote -v` command, the following reposiotries shold be visible:
        * `upstream`, which refers to the SPyCCI repository
        * `origin`, which refers to your personal fork

* Developing your contributions:
    
    * Pull the latest changes from upstream:
        ```
        git checkout main
        git pull upstream main
        ```

    * Create a branch for the feature you want to work on. Since the branch name will appear in the merge message, use a sensible name.:
        ```
        git checkout -b the_name_of_the_branch
        ```

    * Commit locally as you progress (`git add` and `git commit`) and use a properly formatted commit message. If possible, write tests that fail before your change and pass afterward, run all the tests locally. Be aware that the whole suite of tests can be run using `pytest --cov`. More informations about testing can be found in the [dedicated section](testing-info). Before the commit use `tox` to verify the compatibility with all the supported version of python (`tox` will run only unit tests if executed using the provided `tox.ini` configuration file). Be sure to document any changed behavior in docstrings, keeping to the [NumPy docstring standard](https://numpydoc.readthedocs.io/en/latest/format.html). Sphinx annotation are very welcome. If brand new functionality are added to the package make sure to update the documentation as well.

* To submit your contribution:

    * Push your changes back to your fork on GitHub:
        ```
        git push origin the_name_of_the_branch
        ```
    * Follow the GitHub authentication process.

    * Go to GitHub. The new branch will show up with a green Pull Request button. Make sure the title and message are clear, concise, and self- explanatory. Then click the button to submit it.

    * Ask for review from the development team.

## Basics of local development

If you are new to developing python software we strongly advise you to create a local virtual environemnt using Conda or similar tools. Once you have done so, you can install the library in your environment entering, once inside the main `SPyCCI` folder, the command:

```
pip install -e .
```

This will install the python pacakge in editable mode making all the changes you have made immediately effective. To test the functionality of the library you can use the existing tests that can be run using `pytest`. To do so, you can install the development requirements using the provided `requirements_dev.txt`. To do so you can use the command:

```
pip install -r requirements_dev.txt
```

All the tests can be run using the command `pytest --cov` as explained above.

(testing-info)=
### More info about testing
Testing in the SPyCCI library has been divided into three categories:

* `unit`: All the tests related to the inner workings of the library, the object definitions and all the sanity checks concerning data integrity and interactions between class objects.
* `integration`: All the tests related to the interaction between `SPyCCI` and the calculation softwares. These test are intended to verify the correctness of the submitted calculations and the results obtained from the parsing routines.
* `functional`: All the rest related to the operation of composite functions involving one or more calculation software and further data processing by `SPyCCI` itself.

As such, `unit` test can be run without any third party software while `integration` and `functional` tests require the computational softwares to be available. 

:::{admonition} Third party software versions
:class: danger
For the current version of `SPyCCI` the following version of third party software are **required** for testing:

* orca `6.0.1`
* xtb `6.7.1`
* crest `3.0.2`
* dftb+ `24.1`
* packmol `20.14.2`

**Compatibility of the available test with other versions must be verified.**
:::

Specific test groups can be run explicitly by referencing the corresponding folder or script. For example, the command:

```
pytest tests/unit
```

will run only the unit tests, while the command:

```
pytest tests/integration/test_orca_integration.py 
```

will run only the integration tests for the ORCA engine.

If a specific test needs to be executed (e.g., for development purposes), it can be selected using the `::` syntax. For example, the command:

```
pytest tests/integration/test_orca_integration.py::test_cosmors_solventfile
```

will run only the `test_cosmors_solventfile` from the integration tests for the ORCA engine.