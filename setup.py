from setuptools import setup, find_packages

setup(
    name='gsm_ss7_monitor',
    version='1.0.0',
    description='GSM/SS7 Monitoring System',
    author='B13',
    author_email='b13@example.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'': ['*.yaml', '*.yml', '*.json']},
    include_package_data=True,
    install_requires=[
        'flask==2.3.3',
        'python-dotenv==0.21.1',
        'pymongo==4.10.1',
        'scapy==2.5.0',
        'psutil==5.9.5',
        'phonenumbers==8.13.29',
        'docker==6.1.3',
        'kubernetes==28.1.0',
        'paramiko==2.12.0',
        'pytest==7.4.3',
        'pytest-asyncio==0.21.1',
        'pytest-cov==4.1.0',
        'coverage[toml]>=5.2.1',
        'aiohttp==3.9.1',
        'aiozmq==0.9.0',
        'python-jose[cryptography]==3.3.0',
        'python-socketio==5.10.0',
        'elasticsearch==8.9.0',
        'black==23.11.0',
        'isort==5.12.0',
        'mypy==1.7.0',
        'flake8==6.1.0',
        'sphinx>=7.0.1',
        'sphinx-rtd-theme>=1.2.0',
        'sphinx-autodoc-typehints==1.24.0'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'gsm-ss7-monitor=src.__main__:main'
        ]
    }
)
