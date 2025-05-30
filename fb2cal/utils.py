import base64
import struct
import datetime
import binascii

from Cryptodome import Random
from Cryptodome.Cipher import AES
from nacl.public import PublicKey, SealedBox

from .facebook_user import FacebookUser

# Generates permalink to Facebook profile url
# This is needed in many cases as the vanity url may change over time
def generate_facebook_profile_url_permalink(facebook_user: FacebookUser):
    return f'https://www.facebook.com/{facebook_user.id}'

# Facebook prepends an infinite while loop to their API responses as anti hijacking protection
# It must be stripped away before parsing a response as JSON
def remove_anti_hijacking_protection(text: str):
    return text.removeprefix("for (;;);")

# Encryption used on plain text passwords before they are sent to Facebook.
# This function uses the #PWD_BROWSER type which is for Facebook Web requests.
#
# Credits to Lorenzo Di Fuccia: https://gist.github.com/lorenzodifuccia/c857afa47ede66db852e6a25c0a1a027
#
# TODO: Avoid hardcoding the version 5 (instagram has: https://www.instagram.com/data/shared_data/)
def facebook_web_encrypt_password(key_id, pub_key, password, version=5):
    key = Random.get_random_bytes(32)
    iv = bytes([0] * 12)

    time = int(datetime.datetime.now().timestamp())

    aes = AES.new(key, AES.MODE_GCM, nonce=iv, mac_len=16)
    aes.update(str(time).encode('utf-8'))
    encrypted_password, cipher_tag = aes.encrypt_and_digest(password.encode('utf-8'))

    pub_key_bytes = binascii.unhexlify(pub_key)
    seal_box = SealedBox(PublicKey(pub_key_bytes))
    encrypted_key = seal_box.encrypt(key)

    encrypted = bytes([1,
                       key_id,
                       *list(struct.pack('<h', len(encrypted_key))),
                       *list(encrypted_key),
                       *list(cipher_tag),
                       *list(encrypted_password)])
    encrypted = base64.b64encode(encrypted).decode('utf-8')

    return f'#PWD_BROWSER:{version}:{time}:{encrypted}'

# Convert string to boolean based on if its truthy or falsy
def strtobool(val):
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"invalid truth value {val!r}")
