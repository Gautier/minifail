from setuptools import setup, find_packages

setup(
    name='minifail',
    version='0.1',
    description='',
    author='Gautier Hayoun',
    license='Private',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'minifail = minifail.main:main',
        ]
    },
    install_requires=['docopt==0.5.0'],
)

