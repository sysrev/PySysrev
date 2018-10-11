from setuptools import setup

setup(name='PySysrev',
      version='0.8',
      description='Gets annotations from Sysrev API',
      url='https://github.com/sysrev/PySysrev',
      author='nole-lin',
      author_email='nole@insilica.co',
      packages=['PySysrev'],
      install_requires=[
          'pandas',
          'requests',
          'spacy',
          'plac',
          'pathlib'
      ],
      zip_safe=False)
