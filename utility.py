def read_file_content(filepath: str) -> str:
    """
    Reads and returns the content of the given file.
    
    Args:
        filepath (str): Absolute or relative path to the file.

    Returns:
        str: Content of the file as a string.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file can't be decoded with UTF-8.
        Exception: For any other file reading issues.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ File not found: {filepath}")
    except UnicodeDecodeError:
        raise UnicodeDecodeError(f"❌ File encoding issue in: {filepath}")
    except Exception as e:
        raise Exception(f"❌ Unexpected error reading file '{filepath}': {e}")
