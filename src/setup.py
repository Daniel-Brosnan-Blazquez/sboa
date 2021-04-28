"""
Setup configuration for the sboa application

Written by DEIMOS Space S.L. (dibb)

module sboa
"""
from setuptools import setup, find_packages

setup(name="sboa",
      version="1.0.0",
      description="Framework for Sentinel Business Operation Analysis",
      author="Daniel Brosnan",
      author_email="daniel.brosnan@deimos-space.com",
      packages=find_packages(),
      include_package_data=True,
      python_requires='>=3',
      install_requires=[
          "eboa",
          "vboa",
          "astropy",
          "massedit"
      ],
      test_suite='nose.collector')
