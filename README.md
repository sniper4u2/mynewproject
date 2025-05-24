# B13 C2 Server

A comprehensive Command & Control (C2) server with support for various protocols and tools.

## Features

- Web-based management interface
- Multiple protocol support (GSM/SS7, DNS Tunneling, MQTT, CoAP)
- Secure communication with encryption
- Database integration for session management
- Real-time monitoring and control
- Mobile device interception capabilities

## Project Structure

```
src/
├── core/           # Core server functionality
├── protocols/      # Protocol implementations
├── handlers/       # Protocol handlers
├── adapters/       # Protocol adapters
├── utils/          # Utility functions
├── database/       # Database models and operations
└── web/           # Web interface
    ├── templates/  # HTML templates
    └── static/     # Static assets

```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the server:
- Copy `config/config.yaml.example` to `config/config.yaml`
- Update configuration values as needed

4. Initialize the database:
```bash
python init_db.py
```

5. Start the server:
```bash
./start_server.sh
```

## Configuration

The server uses YAML configuration files located in the `config` directory. Main configuration options include:

- Database settings
- Protocol configurations
- Security settings
- Web interface settings

## Security

The server implements multiple security layers:

1. **Authentication**:
   - JWT-based authentication
   - Secure session management
   - Role-based access control

2. **Encryption**:
   - Fernet encryption for sensitive data
   - Secure key management
   - Key rotation support

3. **Rate Limiting**:
   - Configurable API rate limits
   - Exponential backoff
   - Automatic key rotation

4. **Secure Storage**:
   - Encrypted API keys
   - Secure environment variables
   - Protected configuration files

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
