from setuptools import setup

# Assuming your README file is in Markdown
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='sysrev',
    version='1.3.13',
    description='get sysrev project data and use the sysrev api',
    long_description=long_description,
    long_description_content_type='text/markdown',  # Specify the content type here
    url='https://github.com/sysrev/PySysrev',
    author='Thomas Luechtefeld',
    author_email='tom@insilica.co',
    packages=['sysrev'],
    install_requires=['requests'],
    python_requires='>=3.6',
    zip_safe=False
)
