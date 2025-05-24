import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import getpass

def generate_key(password: str) -> bytes:
    """Generate a secure encryption key from a password"""
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_key(key: bytes, encryption_key: bytes) -> str:
    """Encrypt the encryption key using Fernet encryption"""
    fernet = Fernet(encryption_key)
    encrypted = fernet.encrypt(key)
    return encrypted.decode()

def main():
    # Get master password
    password = getpass.getpass("Enter master password: ")
    confirm_password = getpass.getpass("Confirm master password: ")
    
    if password != confirm_password:
        print("Passwords do not match!")
        return
    
    # Generate encryption key
    encryption_key, salt = generate_key(password)
    
    # Store salt in a secure location
    with open('.salt', 'wb') as f:
        f.write(salt)
    
    # Generate encryption key
    key = Fernet.generate_key()
    
    # Encrypt the encryption key
    encrypted_key = encrypt_key(key, encryption_key)
    
    # Update .env file
    with open('.env', 'r') as f:
        env_content = f.read()
    
    # Find and replace encryption key
    lines = env_content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('ENCRYPTION_KEY='):
            lines[i] = f'ENCRYPTION_KEY={encrypted_key}'
    
    with open('.env', 'w') as f:
        f.write('\n'.join(lines))
    
    # Store the encryption key securely
    with open('encryption.key', 'wb') as f:
        f.write(key)
    
    print("Encryption key has been securely generated and stored!")

if __name__ == '__main__':
    main()
