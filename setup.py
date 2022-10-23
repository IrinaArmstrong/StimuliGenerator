from distutils.core import setup
from setuptools import find_packages


def parse_requirements(filename):
    """Load requirements from a pip requirements file."""
    with open(filename, "r") as f:
        lineiter = [line.strip() for line in f]
    return [line for line in lineiter if line and not line.startswith("#")]


main_requirements = parse_requirements("requirements.txt")

config = {
    'name': 'stimuli_generator',
    'author': 'Irina Abdullaeva',
    'author_email': 'a.irene.a@mail.ru',
    'url': 'https://github.com/IrinaArmstrong',
    'description': 'Visual stimulus generation library',
    'long_description': open('README.rst', 'r').read(),
    'license': 'MIT',
    'version': '0.5.0',
    'install_requires': main_requirements,
    'packages': find_packages(),
}

if __name__ == '__main__':
    setup(**config)