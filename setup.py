import setuptools


setuptools.setup(
    name="GES-comp-echem",
    version="0.1.26a",
    description="",
    long_description="",
    packages=["compechem"],
    package_data={"compechem": ["algorithms/*","calculators/*","functions/*"],},
    install_requires=[],
)
