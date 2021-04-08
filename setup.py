from setuptools import setup, find_packages

DESCRIPTION = 'My first Python package'
LONG_DESCRIPTION = 'My first Python package with a slightly longer description'

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name='deemon',
    version='0.1.0',
    author="X",
    author_email="X",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=['deemon'],
    install_requires=['deemix'],
    entry_points = {
        'console_scripts': ['deemon=deemon.deemon:main'],
    }
)
