from setuptools import setup

setup(name='sysrev',
      version='1.2.2',
      description='Gets annotations from Sysrev API',
      url='https://github.com/sysrev/PySysrev',
      author='Thomas Luechtefeld',
      author_email='tom@insilica.co',
      packages=['sysrev'],
      install_requires=[
          'pandas',
          'requests',
          'pathlib'
      ],
      python_requires='>=3.6',
      zip_safe=False)
