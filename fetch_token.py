import requests
import re
import json
from urllib.parse import unquote
from typing import List, Tuple, Optional # Optional is used for last_error type hint

# Equivalent to the JavaScript appDetailsTokenUrls constant
# Using a tuple as it's immutable
APP_DETAILS_TOKEN_URLS: Tuple[str, ...] = (
    'https://apps.apple.com/404',
    'https://apps.apple.com/story/id1538632801',
    'https://apps.apple.com/us/app/facebook/id284882215',
)

# Define a custom exception for clarity, inheriting from Exception
class MediaApiTokenError(Exception):
    """Custom exception raised when the Media API token cannot be fetched."""
    pass

def fetch_media_api_token() -> str:
    """
    Fetch a token for Apple's media API (amp-api.apps.apple.com).

    The token can be used many times (until it expires). It is extracted
    from the HTML of an App Store page.

    The token appears to be the same for everyone and changes periodically
    (around every four months). It is a JWT.

    Raises:
        MediaApiTokenError: If the token cannot be fetched after trying all URLs.

    Returns:
        The media API token string.
    """
    last_error: Optional[Exception] = None
    # Define a user-agent, as some servers might block default python requests User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # Add a timeout to requests to prevent indefinite hanging
    timeout_seconds = 10

    for url in APP_DETAILS_TOKEN_URLS:
        try:
            # Make the HTTP GET request
            response = requests.get(url, headers=headers, timeout=timeout_seconds)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            html = response.text

            # Regex to find the meta tag and extract its content
            # Using raw string (r"...") for the regex pattern
            match = re.search(
                r'<meta name="web-experience-app/config/environment" content="(.+?)">',
                html
            )

            if not match:
                # If regex doesn't match, try the next URL
                continue

            # Extract the captured group (the content attribute)
            encoded_content = match.group(1)
            if not encoded_content:
                 continue # Content is empty

            # Decode the URL-encoded content
            decoded_content = unquote(encoded_content)

            # Parse the decoded content as JSON
            config = json.loads(decoded_content)

            # Navigate the dictionary and get the token
            # Use .get() for safer access, or handle potential KeyErrors
            media_api_config = config.get('MEDIA_API')
            if media_api_config:
                token = media_api_config.get('token')
                if token:
                    return token # Success! Return the token

        # Catch specific exceptions for better error handling
        except requests.exceptions.RequestException as e:
            # Network error, timeout, bad status code, etc.
            last_error = e
        except json.JSONDecodeError as e:
            # Error parsing the JSON content
            last_error = e
        except (KeyError, TypeError, AttributeError) as e:
             # Error accessing keys in the parsed config (e.g., MEDIA_API or token missing)
             # TypeError/AttributeError might occur if structure isn't as expected (e.g., config is not dict)
            last_error = e
        except Exception as e:
            # Catch any other unexpected exceptions
            last_error = e
            # Optionally log this unexpected error
            # print(f"Unexpected error processing {url}: {e}")

    # If the loop finishes without returning a token, raise the custom error
    raise MediaApiTokenError(
        f"Failed to fetch token for media API after trying {len(APP_DETAILS_TOKEN_URLS)} URLs."
    ) from last_error # Include the last caught error as the cause


# Example usage:
if __name__ == "__main__":
    try:
        print("Fetching Media API token...")
        api_token = fetch_media_api_token()
        print(f"Successfully fetched token (first 10 chars): {api_token[:10]}...")
        # You can now use this token in subsequent API calls
    except MediaApiTokenError as e:
        print(f"Error: {e}")
        if e.__cause__:
            print(f"  Caused by: {type(e.__cause__).__name__}: {e.__cause__}")
    except Exception as e:
         print(f"An unexpected error occurred: {e}")import requests
import re
import json
from urllib.parse import unquote
from typing import List, Tuple, Optional # Optional is used for last_error type hint

# Equivalent to the JavaScript appDetailsTokenUrls constant
# Using a tuple as it's immutable
APP_DETAILS_TOKEN_URLS: Tuple[str, ...] = (
    'https://apps.apple.com/404',
    'https://apps.apple.com/story/id1538632801',
    'https://apps.apple.com/us/app/facebook/id284882215',
)

# Define a custom exception for clarity, inheriting from Exception
class MediaApiTokenError(Exception):
    """Custom exception raised when the Media API token cannot be fetched."""
    pass

def fetch_media_api_token() -> str:
    """
    Fetch a token for Apple's media API (amp-api.apps.apple.com).

    The token can be used many times (until it expires). It is extracted
    from the HTML of an App Store page.

    The token appears to be the same for everyone and changes periodically
    (around every four months). It is a JWT.

    Raises:
        MediaApiTokenError: If the token cannot be fetched after trying all URLs.

    Returns:
        The media API token string.
    """
    last_error: Optional[Exception] = None
    # Define a user-agent, as some servers might block default python requests User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # Add a timeout to requests to prevent indefinite hanging
    timeout_seconds = 10

    for url in APP_DETAILS_TOKEN_URLS:
        try:
            # Make the HTTP GET request
            response = requests.get(url, headers=headers, timeout=timeout_seconds)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            html = response.text

            # Regex to find the meta tag and extract its content
            # Using raw string (r"...") for the regex pattern
            match = re.search(
                r'<meta name="web-experience-app/config/environment" content="(.+?)">',
                html
            )

            if not match:
                # If regex doesn't match, try the next URL
                continue

            # Extract the captured group (the content attribute)
            encoded_content = match.group(1)
            if not encoded_content:
                 continue # Content is empty

            # Decode the URL-encoded content
            decoded_content = unquote(encoded_content)

            # Parse the decoded content as JSON
            config = json.loads(decoded_content)

            # Navigate the dictionary and get the token
            # Use .get() for safer access, or handle potential KeyErrors
            media_api_config = config.get('MEDIA_API')
            if media_api_config:
                token = media_api_config.get('token')
                if token:
                    return token # Success! Return the token

        # Catch specific exceptions for better error handling
        except requests.exceptions.RequestException as e:
            # Network error, timeout, bad status code, etc.
            last_error = e
        except json.JSONDecodeError as e:
            # Error parsing the JSON content
            last_error = e
        except (KeyError, TypeError, AttributeError) as e:
             # Error accessing keys in the parsed config (e.g., MEDIA_API or token missing)
             # TypeError/AttributeError might occur if structure isn't as expected (e.g., config is not dict)
            last_error = e
        except Exception as e:
            # Catch any other unexpected exceptions
            last_error = e
            # Optionally log this unexpected error
            # print(f"Unexpected error processing {url}: {e}")

    # If the loop finishes without returning a token, raise the custom error
    raise MediaApiTokenError(
        f"Failed to fetch token for media API after trying {len(APP_DETAILS_TOKEN_URLS)} URLs."
    ) from last_error # Include the last caught error as the cause


# Example usage:
if __name__ == "__main__":
    try:
        print("Fetching Media API token...")
        api_token = fetch_media_api_token()
        print(f"Successfully fetched token (first 10 chars): {api_token[:10]}...")
        # You can now use this token in subsequent API calls
    except MediaApiTokenError as e:
        print(f"Error: {e}")
        if e.__cause__:
            print(f"  Caused by: {type(e.__cause__).__name__}: {e.__cause__}")
    except Exception as e:
         print(f"An unexpected error occurred: {e}")
