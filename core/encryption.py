"""
ContextOS Encryption Module.

Provides AES-256-GCM encryption and decryption for data at rest.
Uses PBKDF2 key derivation from the configured encryption key.
"""

import hashlib
import logging
import os
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.config import settings

logger = logging.getLogger(__name__)

# Constants
SALT_SIZE = 16  # bytes
NONCE_SIZE = 12  # bytes for AES-GCM
KEY_LENGTH = 32  # bytes for AES-256
KDF_ITERATIONS = 480_000  # OWASP recommended minimum for PBKDF2-SHA256
TEST_PLAINTEXT = "contextos-encryption-verification-string"


class EncryptionError(Exception):
    """Raised when an encryption or decryption operation fails."""


class Encryptor:
    """
    AES-256-GCM encryption/decryption utility for ContextOS.

    Derives a 256-bit key from the configured encryption key using PBKDF2.
    Each encrypt operation generates a unique salt and nonce, prepended
    to the ciphertext for self-contained decryption.

    Wire format: salt (16 bytes) || nonce (12 bytes) || ciphertext (variable)
    """

    def __init__(self, key: str | None = None) -> None:
        """
        Initialize the Encryptor with a key string.

        Args:
            key: The encryption key string. If None, uses the value from settings.

        Raises:
            EncryptionError: If no encryption key is available.
        """
        self._key_material = key or settings.CONTEXTOS_ENCRYPTION_KEY
        if not self._key_material:
            raise EncryptionError(
                "No encryption key configured. Set CONTEXTOS_ENCRYPTION_KEY in .env"
            )
        logger.debug("Encryptor initialized.")

    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive a 256-bit AES key from the key material using PBKDF2.

        Args:
            salt: A random salt for key derivation.

        Returns:
            A 32-byte derived key suitable for AES-256.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=KDF_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(self._key_material.encode("utf-8"))

    def encrypt(self, data: str) -> bytes:
        """
        Encrypt a string using AES-256-GCM.

        Generates a random salt and nonce for each encryption operation.
        The output format is: salt || nonce || ciphertext.

        Args:
            data: The plaintext string to encrypt.

        Returns:
            Encrypted bytes containing salt, nonce, and ciphertext.

        Raises:
            EncryptionError: If encryption fails for any reason.
        """
        try:
            salt = os.urandom(SALT_SIZE)
            nonce = os.urandom(NONCE_SIZE)
            key = self._derive_key(salt)
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), None)
            return salt + nonce + ciphertext
        except Exception as exc:
            logger.error("Encryption failed: %s", exc)
            raise EncryptionError(f"Encryption failed: {exc}") from exc

    def decrypt(self, data: bytes) -> str:
        """
        Decrypt AES-256-GCM encrypted bytes back to a string.

        Extracts salt, nonce, and ciphertext from the input, derives the key
        using the same salt, and decrypts.

        Args:
            data: Encrypted bytes in the format: salt || nonce || ciphertext.

        Returns:
            The decrypted plaintext string.

        Raises:
            EncryptionError: If decryption fails (wrong key, tampered data, etc.)
        """
        try:
            if len(data) < SALT_SIZE + NONCE_SIZE + 1:
                raise EncryptionError(
                    "Encrypted data too short — likely corrupted or invalid."
                )
            salt = data[:SALT_SIZE]
            nonce = data[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
            ciphertext = data[SALT_SIZE + NONCE_SIZE :]
            key = self._derive_key(salt)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except EncryptionError:
            raise
        except Exception as exc:
            logger.error("Decryption failed: %s", exc)
            raise EncryptionError(f"Decryption failed: {exc}") from exc

    def encrypt_file(self, src: Path, dst: Path) -> None:
        """
        Encrypt a file from src and write the ciphertext to dst.

        Args:
            src: Path to the source plaintext file.
            dst: Path to write the encrypted output.

        Raises:
            EncryptionError: If the file cannot be read or encryption fails.
            FileNotFoundError: If the source file does not exist.
        """
        try:
            plaintext = src.read_text(encoding="utf-8")
            encrypted = self.encrypt(plaintext)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(encrypted)
            logger.info("Encrypted file %s → %s", src, dst)
        except FileNotFoundError:
            logger.error("Source file not found: %s", src)
            raise
        except EncryptionError:
            raise
        except Exception as exc:
            logger.error("File encryption failed: %s", exc)
            raise EncryptionError(f"File encryption failed: {exc}") from exc

    def decrypt_file(self, src: Path, dst: Path) -> None:
        """
        Decrypt a file from src and write the plaintext to dst.

        Args:
            src: Path to the encrypted source file.
            dst: Path to write the decrypted output.

        Raises:
            EncryptionError: If decryption fails.
            FileNotFoundError: If the source file does not exist.
        """
        try:
            encrypted = src.read_bytes()
            plaintext = self.decrypt(encrypted)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(plaintext, encoding="utf-8")
            logger.info("Decrypted file %s → %s", src, dst)
        except FileNotFoundError:
            logger.error("Encrypted file not found: %s", src)
            raise
        except EncryptionError:
            raise
        except Exception as exc:
            logger.error("File decryption failed: %s", exc)
            raise EncryptionError(f"File decryption failed: {exc}") from exc

    def verify_key(self) -> bool:
        """
        Verify that the encryption key works by round-tripping a test string.

        Returns:
            True if encryption and decryption succeed with the current key.

        Raises:
            EncryptionError: If the round-trip verification fails.
        """
        try:
            encrypted = self.encrypt(TEST_PLAINTEXT)
            decrypted = self.decrypt(encrypted)
            if decrypted != TEST_PLAINTEXT:
                raise EncryptionError(
                    "Key verification failed: round-trip mismatch."
                )
            logger.info("Encryption key verified successfully.")
            return True
        except EncryptionError:
            raise
        except Exception as exc:
            raise EncryptionError(
                f"Key verification failed: {exc}"
            ) from exc
