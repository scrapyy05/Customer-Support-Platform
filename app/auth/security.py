from passlib.context import CryptContext

# Passlib CryptContext using bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies that a plaintext password matches its hashed bcrypt counterpart.
    """
    return pwd_context.verify(plain_password, hashed_password)
