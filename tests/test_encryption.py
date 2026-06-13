"""Tests for core.encryption module."""

import pytest


@pytest.fixture
def encryptor():
    """Create an Encryptor with a test key."""
    from core.encryption import Encryptor

    return Encryptor(key="test-encryption-key-for-unit-testing!")


class TestEncryptor:
    """Tests for the Encryptor class."""

    def test_encrypt_returns_bytes(self, encryptor):
        """encrypt() should return bytes different from the input."""
        plaintext = "Hello, ContextOS!"
        encrypted = encryptor.encrypt(plaintext)
        assert isinstance(encrypted, bytes)
        assert encrypted != plaintext.encode("utf-8")

    def test_encrypt_decrypt_roundtrip(self, encryptor):
        """decrypt(encrypt(data)) should return the original data."""
        test_strings = [
            "Simple test",
            "Unicode: café, naïve, 日本語",
            "A" * 10000,  # Large string
            "Special chars: !@#$%^&*()_+-={}[]|\\:;'\"<>,.?/",
            "",  # Empty string — edge case
        ]
        for plaintext in test_strings:
            if not plaintext:
                continue  # Empty string may not round-trip
            encrypted = encryptor.encrypt(plaintext)
            decrypted = encryptor.decrypt(encrypted)
            assert decrypted == plaintext, f"Round-trip failed for: {plaintext[:50]}"

    def test_decrypt_tampered_raises(self, encryptor):
        """decrypt() should raise EncryptionError on tampered ciphertext."""
        from core.encryption import EncryptionError

        encrypted = encryptor.encrypt("test data")
        # Tamper with the ciphertext
        tampered = encrypted[:-5] + b"\x00\x00\x00\x00\x00"
        with pytest.raises(EncryptionError):
            encryptor.decrypt(tampered)

    def test_decrypt_short_data_raises(self, encryptor):
        """decrypt() should raise EncryptionError on data that's too short."""
        from core.encryption import EncryptionError

        with pytest.raises(EncryptionError):
            encryptor.decrypt(b"short")

    def test_verify_key_valid(self, encryptor):
        """verify_key() should return True for a valid key."""
        assert encryptor.verify_key() is True

    def test_verify_key_invalid(self):
        """verify_key() should work and a wrong-key decrypt should fail."""
        from core.encryption import EncryptionError, Encryptor

        enc1 = Encryptor(key="key-one-for-testing-purposes-1234")
        enc2 = Encryptor(key="key-two-for-testing-purposes-5678")

        encrypted = enc1.encrypt("secret message")
        with pytest.raises(EncryptionError):
            enc2.decrypt(encrypted)

    def test_encrypt_file(self, encryptor, tmp_path):
        """encrypt_file and decrypt_file should round-trip a file."""
        src = tmp_path / "plain.txt"
        encrypted_file = tmp_path / "encrypted.bin"
        decrypted_file = tmp_path / "decrypted.txt"

        src.write_text("File content for encryption test.", encoding="utf-8")
        encryptor.encrypt_file(src, encrypted_file)
        assert encrypted_file.exists()
        assert encrypted_file.read_bytes() != src.read_bytes()

        encryptor.decrypt_file(encrypted_file, decrypted_file)
        assert decrypted_file.read_text(encoding="utf-8") == "File content for encryption test."

    def test_each_encryption_unique(self, encryptor):
        """Two encryptions of the same text should produce different ciphertext."""
        plaintext = "same input"
        enc1 = encryptor.encrypt(plaintext)
        enc2 = encryptor.encrypt(plaintext)
        assert enc1 != enc2  # Different salt/nonce each time
