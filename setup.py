from setuptools import setup, find_packages
#Run pip install . to install all files here
#If there is no setup.py, do git submodule add {gitlink.git}

#TODO: Add a bash that downloads the submodule and runs setup.py

#Run python -m pip install -r requirements.txt to install all dependencies
# OR pip install .
setup(
    name='HogSlice',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        "vtk==9.4.0",
        "PyQt5>=5.15",
    ]
)