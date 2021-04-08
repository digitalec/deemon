from setuptools import setup, find_packages

DESCRIPTION = 'Monitor new releases by a specified list of artists and auto download using the deemix library'
LONG_DESCRIPTION = DESCRIPTION

setup(
    name='deemon',
    version='0.1.2',
    author='digitalec',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=['deemix>=2.0.1', 'deezer-py>=0.0.15'],
    url='https://github.com/digitalec/deemon',
    entry_points = {
        'console_scripts': ['deemon=deemon.__main__:main'],
    }
)
