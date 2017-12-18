from setuptools import setup

setup(
    name='questions',
    version='1.0',
    description='UvA questions module',
    packages=['questions'],
    author='Jesse van der Sar',
    author_email='j.d.vandersar@uva.nl',
    install_requires=[
        'ipywidgets',
        'ipython',
        'jupyter'
    ],
)