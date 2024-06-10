import json, hashlib


def stable_json_hash(data):
    """
    Returns a consistent hash for a JSON object.

    This function serializes the given JSON data in a consistent order (sort_keys=True)
    and computes its SHA256 hash. This is useful for generating a unique identifier
    for JSON objects that may have their keys in arbitrary order.

    Parameters:
    - data (dict): The JSON object to hash.

    Returns:
    - str: The hexadecimal digest of the hash.
    """
    # Serialize the JSON data with keys sorted to ensure consistency,
    # then encode it to bytes as required by hashlib.
    serialized_data = json.dumps(data, sort_keys=True).encode("utf-8")
    # Create a SHA256 hash object from the serialized data.
    hash_object = hashlib.sha256(serialized_data)
    # Return the hexadecimal representation of the digest.
    return hash_object.hexdigest()


def generate_database_name(file_name):
    """
    Generates a unique database name based on the file name's SHA256 hash.

    This function computes the SHA256 hash of the given file name, prefixes the hash
    with a letter to ensure it doesn't start with a number (for compatibility reasons),
    and truncates it to 63 characters.

    Parameters:
    - file_name (str): The file name to hash.

    Returns:
    - str: A database name derived from the file name's hash.
    """
    # Compute the SHA256 hash of the file name after encoding it to bytes.
    hash_object = hashlib.sha256(file_name.encode())
    # Prefix the hexadecimal digest with 'd' and limit its length to 63 characters.
    database_name = "d" + hash_object.hexdigest()[:63]
    return database_name
