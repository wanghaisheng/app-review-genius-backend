import requests
import re
import json
from urllib.parse import unquote, urlencode
from typing import List, Dict, Any, Optional, Tuple, TypedDict, Literal

# --- Dependencies (Assuming these types exist elsewhere or simplifying) ---

# If you have specific definitions for these, import them.
# Otherwise, we might use broader types like str or Literal for demonstration.

# Example Simplification/Placeholders:
MediaApiCountry = str # e.g., 'us', 'gb', 'de'
AllowedLanguagesPerCountryInMediaApi = Dict[MediaApiCountry, str] # Placeholder structure
AppDetailsPlatformInRequest = Literal['ios', 'macos', 'appletv', 'watchos', 'web', 'ipad', 'iphone', 'mac', 'watch'] # Example values
AppDetailsAvailableAttribute = str # e.g., 'name', 'artistName', 'userRating', etc.
AppDetailsPlatformInResponse = str # The platforms keys that might appear *in* the response
# AppDetailsPlatformInResponseForRequest mapping isn't directly used in the runtime logic shown
# AppDetailsResponseFragmentPerAttribute isn't directly representable in Python's static types easily

# --- Token Fetching Code (from previous conversion) ---

APP_DETAILS_TOKEN_URLS: Tuple[str, ...] = (
    'https://apps.apple.com/404',
    'https://apps.apple.com/story/id1538632801',
    'https://apps.apple.com/us/app/facebook/id284882215',
)

class MediaApiTokenError(Exception):
    """Custom exception raised when the Media API token cannot be fetched."""
    pass

def fetch_media_api_token() -> str:
    """
    Fetch a token for Apple's media API (amp-api.apps.apple.com).

    The token is extracted from the HTML of an App Store page.

    Raises:
        MediaApiTokenError: If the token cannot be fetched after trying all URLs.

    Returns:
        The media API token string.
    """
    last_error: Optional[Exception] = None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    timeout_seconds = 10

    for url in APP_DETAILS_TOKEN_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
            html = response.text

            match = re.search(
                r'<meta name="web-experience-app/config/environment" content="(.+?)">',
                html
            )
            if not match:
                continue

            encoded_content = match.group(1)
            if not encoded_content:
                 continue

            decoded_content = unquote(encoded_content)
            config = json.loads(decoded_content)

            media_api_config = config.get('MEDIA_API')
            if media_api_config:
                token = media_api_config.get('token')
                if token and isinstance(token, str): # Ensure token is a non-empty string
                    return token

        except requests.exceptions.RequestException as e:
            last_error = e
        except json.JSONDecodeError as e:
            last_error = e
        except (KeyError, TypeError, AttributeError) as e:
            last_error = e
        except Exception as e:
            last_error = e

    raise MediaApiTokenError(
        f"Failed to fetch token for media API after trying {len(APP_DETAILS_TOKEN_URLS)} URLs."
    ) from last_error

# --- App Details Code ---

class AppDetailsRequest(TypedDict):
    """
    Parameters for an app details request.
    Corresponds to the TypeScript AppDetailsRequest type.
    """
    appId: int
    attributes: List[AppDetailsAvailableAttribute]
    country: MediaApiCountry
    language: str # Simplified from AllowedLanguagesPerCountryInMediaApi[Country]
    platforms: Optional[List[AppDetailsPlatformInRequest]] # Optional field
    token: Optional[str] # Optional field

def app_details_api_url(request: AppDetailsRequest) -> str:
    """
    Constructs the URL for the Apple Media API app details endpoint.
    """
    base_url = f"https://amp-api.apps.apple.com/v1/catalog/{request['country']}/apps/{request['appId']}"

    # Handle platforms
    platforms = request.get('platforms') # Use .get() for optional field
    primary_platform: AppDetailsPlatformInRequest
    additional_platforms_str: str

    if platforms and len(platforms) > 0:
        primary_platform = platforms[0]
        if len(platforms) > 1:
            additional_platforms_str = ",".join(platforms[1:])
        else:
            additional_platforms_str = "" # No additional platforms
    else:
        # Default behavior if platforms is None or empty
        primary_platform = 'web'
        additional_platforms_str = 'iphone,appletv,ipad,mac,watch'

    # Prepare query parameters
    params: Dict[str, str] = {
        'platform': primary_platform,
        'l': request['language'],
        'fields': ",".join(request['attributes']),
    }
    # Only add additionalPlatforms if it's not empty
    if additional_platforms_str:
        params['additionalPlatforms'] = additional_platforms_str

    # Encode parameters and append to URL
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"


# Note: The complex generic AppDetailsResponse type from TypeScript is simplified
# to Dict[str, Any] here, as Python's type system cannot easily replicate
# the dynamic structure merging (UnionToIntersection based on input attributes).
# The actual dictionary returned will contain keys corresponding to the
# requested 'attributes'.

def fetch_app_details(request: AppDetailsRequest) -> Dict[str, Any]:
    """
    Fetch the details for an app from the App Store.

    You can request a lot of different information about the app. The
    `attributes` parameter specifies which attributes to fetch.

    Args:
        request: The request parameters dictionary, conforming to AppDetailsRequest structure.

    Raises:
        MediaApiTokenError: If a token is needed but cannot be fetched.
        requests.exceptions.RequestException: For network or HTTP errors from the API call.
        KeyError: If the response JSON structure is unexpected.
        IndexError: If the response JSON structure is unexpected.
        json.JSONDecodeError: If the API response is not valid JSON.

    Returns:
        A dictionary containing the requested app details attributes.
        The specific keys depend on the 'attributes' requested.
    """
    # Get token: use provided one or fetch a new one
    token = request.get('token')
    if not token:
        try:
            token = fetch_media_api_token()
        except MediaApiTokenError as e:
            # Re-raise to indicate failure context
            raise MediaApiTokenError("Failed to fetch required API token for app details.") from e


    # Construct the API URL
    api_url = app_details_api_url(request)

    # Prepare headers
    headers = {
        'Authorization': f'Bearer {token}',
        'Origin': 'https://apps.apple.com',
         # Good practice to include User-Agent for external APIs
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Make the API call
    try:
        response = requests.get(api_url, headers=headers, timeout=15) # Add timeout
        response.raise_for_status() # Check for HTTP errors (4xx, 5xx)

        # Parse the JSON response
        res_data = response.json() # requests can directly parse JSON

        # Extract the attributes - includes error handling for structure
        if not isinstance(res_data, dict) or 'data' not in res_data or not isinstance(res_data['data'], list) or len(res_data['data']) == 0:
             raise ValueError("Unexpected API response structure: 'data' array missing or empty.")

        first_app_data = res_data['data'][0]
        if not isinstance(first_app_data, dict) or 'attributes' not in first_app_data:
             raise ValueError("Unexpected API response structure: 'attributes' missing in first data item.")

        attributes_dict = first_app_data['attributes']
        if not isinstance(attributes_dict, dict):
             raise ValueError("Unexpected API response structure: 'attributes' is not a dictionary.")

        return attributes_dict # This is the Dict[str, Any]

    except requests.exceptions.RequestException as e:
        # Includes ConnectionError, HTTPError, Timeout, etc.
        print(f"API Request failed: {e}")
        raise # Re-raise the exception
    except json.JSONDecodeError as e:
        print(f"Failed to parse API response JSON: {e}")
        print(f"Response text: {response.text[:500]}...") # Log part of the bad response
        raise
    except (KeyError, IndexError, ValueError) as e:
        # Raised if the JSON structure doesn't match expectations
        print(f"Unexpected API response structure: {e}")
        print(f"Response data: {res_data}") # Log the problematic structure
        raise


# --- Example Usage ---
if __name__ == "__main__":
    print("--- Example: Fetching App Details for Facebook (US) ---")

    # Define the request parameters
    # Note: 'language' needs to be valid for the chosen 'country' according to Apple's API.
    # Check Apple's documentation or experiment to find valid combinations. 'en-US' usually works for 'us'.
    example_request: AppDetailsRequest = {
        'appId': 284882215, # Facebook App ID
        'attributes': ['name', 'artistName', 'userRating', 'description', 'releaseDate', 'genres'], # Which details to fetch
        'country': 'us',
        'language': 'en-US',
        'platforms': ['ios'], # Specify platform(s) or leave out for default
        # 'token': 'YOUR_PREFETCHED_TOKEN' # Optionally provide a token
    }

    try:
        print(f"Requesting details for App ID: {example_request['appId']}")
        print(f"URL: {app_details_api_url(example_request)}") # Show the generated URL

        app_details = fetch_app_details(example_request)

        print("\n--- Fetched App Details ---")
        # Pretty print the resulting dictionary
        print(json.dumps(app_details, indent=2))

        # Access specific fields
        print(f"\nApp Name: {app_details.get('name', 'N/A')}")
        print(f"Artist: {app_details.get('artistName', 'N/A')}")
        # Note: userRating might be nested, inspect the actual response structure
        user_rating_info = app_details.get('userRating')
        if isinstance(user_rating_info, dict):
             print(f"Average Rating: {user_rating_info.get('value', 'N/A')}")
             print(f"Rating Count: {user_rating_info.get('ratingCount', 'N/A')}")
        else:
             print(f"User Rating Info: {user_rating_info}")


    except MediaApiTokenError as e:
        print(f"\nERROR fetching token: {e}")
        if e.__cause__:
            print(f"  -> Caused by: {type(e.__cause__).__name__}: {e.__cause__}")
    except requests.exceptions.RequestException as e:
        print(f"\nERROR during API request: {e}")
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        print(f"\nERROR processing API response: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {type(e).__name__}: {e}")
