import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import getpass

def load_salt() -> bytes:
    """Load the salt from file"""
    with open('.salt', 'rb') as f:
        return f.read()

def generate_key(password: str, salt: bytes) -> bytes:
    """Generate encryption key from password and salt"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def decrypt_key(encrypted_key: str, encryption_key: bytes) -> bytes:
    """Decrypt the encryption key using Fernet encryption"""
    fernet = Fernet(encryption_key)
    decrypted = fernet.decrypt(encrypted_key.encode())
    return decrypted

def main():
    # Get master password
    password = getpass.getpass("Enter master password: ")
    
    # Load salt
    salt = load_salt()
    
    # Generate encryption key
    encryption_key = generate_key(password, salt)
    
    # Load encrypted encryption key from .env
    with open('.env', 'r') as f:
        env_content = f.read()
    
    # Find encrypted encryption key
    lines = env_content.split('\n')
    encrypted_key = None
    
    for line in lines:
        if line.startswith('ENCRYPTION_KEY='):
            encrypted_key = line.split('=')[1]
            break
    
    if not encrypted_key:
        print("Encryption key not found in .env file")
        return
    
    try:
        # Decrypt encryption key
        key = decrypt_key(encrypted_key, encryption_key)
        
        print("\nDecrypted Encryption Key:")
        print(f"Encryption Key: {key.decode()}")
        
    except Exception as e:
        print(f"Error decrypting encryption key: {str(e)}")
        print("Make sure you entered the correct master password.")

if __name__ == '__main__':
    main()
