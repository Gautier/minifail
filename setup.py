from setuptools import setup, find_packages

setup(
    name='minifail',
    version='0.1',
    description='minifail is a simple IP failover compatible with Linux/BSD/MacOS',
    author='Gautier Hayoun',
    author_email='ghayoun@gmail.com',
    url='https://github.com/gautier/minifail',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'minifail = minifail.main:main',
        ]
    },
    install_requires=['docopt==0.5.0'],
)

