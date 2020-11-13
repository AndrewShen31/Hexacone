from setuptools import setup
from Cython.Build import cythonize

setup(
    name='Hello world app',
    ext_modules=cythonize("graphics/main.pyx"),
    zip_safe=False,
)