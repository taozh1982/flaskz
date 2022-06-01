"""
pip install pycryptodome
"""
import base64
import random
import string

from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Util.Padding import pad, unpad

__all__ = ['RSACipher', 'AESCipher']


class RSACipher:
    """
    The rsa utility class

    The result of the encrypt and sign methods are in base64 format
    """

    @staticmethod
    def generate_key(bits=1024, to_base64=True):
        """
        Generate ras key(private_key, public_key)

        :param bits:
        :param to_base64: if not False, return the key with base64 format

        :return: (private_key, public_key)
        """
        rsa_key = RSA.generate(bits)
        private_key = rsa_key.export_key('PEM').decode('utf-8')
        public_key = rsa_key.public_key().export_key('PEM').decode('utf-8')
        if to_base64 is not False:
            private_key = base64.b64encode(private_key.encode('utf-8')).decode('utf-8')
            public_key = base64.b64encode(public_key.encode('utf-8')).decode('utf-8')
        return private_key, public_key

    @staticmethod
    def encrypt(plaintext, public_key):
        """
        Encrypt data with rsa public key.

        encrypt_key = RSACipher.encrypt(public_key, aes_key)

        :param plaintext: the data to be encrypted
        :param public_key: rsa public key

        :return: ciphertext：the encrypted text(base64 format)
        """
        plaintext = _to_byte(plaintext)
        cipher = PKCS1_OAEP.new(RSACipher._import_rsa_key(public_key), hashAlgo=SHA256)
        return base64.b64encode(cipher.encrypt(plaintext)).decode('utf-8')

    @staticmethod
    def decrypt(ciphertext, private_key):
        """
        Decrypt ciphertext with rsa private key.

        aes_key = RSACipher.decrypt(private_key, encrypt_key)

        :param ciphertext: the data to be decrypted(base64 format)
        :param private_key: rsa private key

        :return: plaintext: the decrypted string
        """
        ciphertext = _to_byte(ciphertext)
        cipher = PKCS1_OAEP.new(RSACipher._import_rsa_key(private_key), hashAlgo=SHA256)
        return cipher.decrypt(base64.b64decode(ciphertext)).decode('utf-8')

    @staticmethod
    def sign(text, private_key):
        """
        Sign the data with the private key

        signature = RSACipher.sign(private_key, aes_key)

        :param text: the text to be signed
        :param private_key: rsa private key

        :return: signature: the signature(base64 format)
        """
        text = _to_byte(text)
        signer = PKCS1_v1_5.new(RSACipher._import_rsa_key(private_key))
        signature = signer.sign(SHA256.new(text))
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def verify(text, signature, public_key):
        """
        Verify the signature

        result = RSACipher.verify(public_key, aes_key, signature)

        :param text: the raw text
        :param signature: the signature(base64 format)
        :param public_key: rsa public key

        :return: result: return True on success, otherwise return False
        """
        text = _to_byte(text)
        try:
            verifier = PKCS1_v1_5.new(RSACipher._import_rsa_key(public_key))
            return verifier.verify(SHA256.new(text), base64.b64decode(signature))
        except (Exception,):
            return False

    @staticmethod
    def _import_rsa_key(key):
        if _is_base64(key):
            key = base64.b64decode(key)
        return RSA.importKey(key)


class AESCipher:
    """
    The aes utility class

    The result of the encrypt is in base64 format
    """

    @staticmethod
    def generate_key():
        """
        Generate a 16-bit random key

        aes_key = AESCipher.generate_key()

        :return: key
        """
        key = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
        return key

    @staticmethod
    def encrypt(plaintext, key, iv=None):
        """
        Encrypt data with aes key and iv.

        encrypt_text = AESCipher.encrypt(data, aes_key)

        :param plaintext: the data to be encrypted
        :param key: the key used to create AES cipher
        :param iv: the iv used to create AES cipher(AES.MODE_CBC), if None, use key as iv.

        :return: ciphertext: the encrypted text(base64 format)
        """
        plaintext = _to_byte(plaintext)
        plaintext = pad(plaintext, AES.block_size)
        key, iv = AESCipher._encode_key_iv(key, iv)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(plaintext)).decode('utf-8')

    @staticmethod
    def decrypt(ciphertext, key, iv=None):
        """
        Decrypt ciphertext with aes key and iv.

        decrypt_text = AESCipher.decrypt(encrypt_text, aes_key)

        :param ciphertext: the ciphertext to be decrypted(base64 format)
        :param key: the key used to decrypt
        :param iv: the iv used to decrypt, if None, use key as iv.

        :return: plaintext: the decrypted string
        """
        ciphertext = _to_byte(ciphertext)
        ciphertext = base64.b64decode(ciphertext)
        key, iv = AESCipher._encode_key_iv(key, iv)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(ciphertext)
        decrypted_data = unpad(decrypted_data, AES.block_size)
        decrypted_data = decrypted_data.decode('utf-8')
        return decrypted_data

    @staticmethod
    def _encode_key_iv(key, iv=None):
        if type(key) is str:
            key = key.encode('utf-8')
        if iv is None:
            iv = key
        elif type(iv) is str:
            iv = iv.encode('utf-8')

        return key, iv


def _is_base64(txt):
    try:
        return base64.b64encode(base64.b64decode(txt)).decode('utf-8') == txt.replace('\n', '').replace(' ', '').strip()
    except Exception:
        return False


def _to_byte(text):
    if type(text) is str:
        return text.encode('utf-8')
    return text


if __name__ == '__main__':
    """
    RSA+AES
    The process of sending encrypted information from the client to the server
    1.The client encrypts the data with the server's public key
    2.The client signs the aes key with the client's private key
    3.The client sends ciphertext and signature to server
    4.The server uses the client's public key to verify the signature
    5.The server uses the server's private key to decrypt the ciphertext
    """
    server_private_key, server_public_key = RSACipher.generate_key()  # just for test
    client_private_key, client_public_key = RSACipher.generate_key()  # just for test

    # --------------------client--------------------
    send_data = 'hello server'
    # Generate aes key
    send_aes_key = AESCipher.generate_key()
    print('--AES Key:%s' % send_aes_key)

    # encrypt [data] with aes key
    send_aes_encrypted_data = AESCipher.encrypt(send_data, send_aes_key)
    print('--Encrypted Data: %s' % send_aes_encrypted_data)

    # sign [aes key] with client rsa private key
    send_aes_key_signature = RSACipher.sign(send_aes_key, client_private_key)
    print('--AES Key Signature: %s' % send_aes_key_signature)

    # encrypt [aes key] with server rsa public key
    send_encrypted_aes_key = RSACipher.encrypt(send_aes_key, server_public_key)
    print('--Encrypted AES Key: %s' % send_encrypted_aes_key)

    # send (send_aes_key_signature, send_encrypted_aes_key, send_aes_encrypted_data)
    print('--send (send_aes_key_signature, send_encrypted_aes_key, send_aes_encrypted_data)')
    print('\n************************************************\n')
    print('--receive (send_aes_key_signature, send_encrypted_aes_key, send_aes_encrypted_data)')
    # receive (send_aes_key_signature, send_encrypted_aes_key, send_aes_encrypted_data)

    # --------------------server--------------------
    # decrypt [aes key] with server rsa private key
    rcv_aes_key = RSACipher.decrypt(send_encrypted_aes_key, server_private_key)
    print('--Decrypted AES Key: %s' % rcv_aes_key)

    # verify aes_key and signature with client rsa public key
    result = RSACipher.verify(rcv_aes_key, send_aes_key_signature, client_public_key)
    print('--Verify AES Key and AES Key Signature: %s' % result)

    # decrypt [data] with [aes key]
    rcv_decrypted_data = AESCipher.decrypt(send_aes_encrypted_data, rcv_aes_key)
    print('--Decypted Data: %s' % rcv_decrypted_data)
