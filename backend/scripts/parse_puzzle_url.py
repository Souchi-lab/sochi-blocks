import urllib.parse

def parse_puzzle_url(url: str):
    """
    Parses a puzzle URL to extract puzzle_id and removed_pieces parameters.

    Args:
        url (str): The URL string to parse.

    Returns:
        tuple: A tuple containing (puzzle_id, removed_pieces_list).
               puzzle_id will be None if not found.
               removed_pieces_list will be an empty list if not found.
    """
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    puzzle_id = query_params.get('puzzle_id', [None])[0]
    removed_pieces_str = query_params.get('removed_pieces', [''])[0]
    
    removed_pieces_list = []
    if removed_pieces_str:
        removed_pieces_list = removed_pieces_str.split(',')

    return puzzle_id, removed_pieces_list

if __name__ == "__main__":
    # Example URL from QR code
    sample_url_with_removed = "http://localhost:8080/viewer?puzzle_id=5x4x3_0000&removed_pieces=V,W"
    sample_url_no_removed = "http://localhost:8080/viewer?puzzle_id=5x4x3_0001"
    sample_url_only_base = "http://localhost:8080/viewer"

    print(f"Parsing URL: {sample_url_with_removed}")
    puzzle_id, removed_pieces = parse_puzzle_url(sample_url_with_removed)
    print(f"  Puzzle ID: {puzzle_id}")
    print(f"  Removed Pieces: {removed_pieces}")
    print("-" * 30)

    print(f"Parsing URL: {sample_url_no_removed}")
    puzzle_id, removed_pieces = parse_puzzle_url(sample_url_no_removed)
    print(f"  Puzzle ID: {puzzle_id}")
    print(f"  Removed Pieces: {removed_pieces}")
    print("-" * 30)

    print(f"Parsing URL: {sample_url_only_base}")
    puzzle_id, removed_pieces = parse_puzzle_url(sample_url_only_base)
    print(f"  Puzzle ID: {puzzle_id}")
    print(f"  Removed Pieces: {removed_pieces}")
    print("-" * 30)
