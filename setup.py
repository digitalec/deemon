from setuptools import setup

DESCRIPTION = 'Monitor new releases by a specified list of artists and auto download using the deemix library'
LONG_DESCRIPTION = DESCRIPTION

# Setting up
setup(
    name='deemon',
    version='0.1.2',
    author='digitalec',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=['deemon'],
    python_requires='>=3.6',
    install_requires=['deemix'],
    url='https://github.com/digitalec/deemon',
    entry_points = {
        'console_scripts': ['deemon=deemon.__main__:main'],
    }
)
