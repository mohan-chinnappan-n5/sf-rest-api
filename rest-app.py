import streamlit as st
import requests
import pandas as pd
import json
from urllib.parse import urljoin

#------------------------------------------------------
# Salesforce REST API Data Fetcher Streamlit Application
# Author: Mohan Chinnappan
# Copyleft software. Maintain the author name in your copies/modifications
#
# Description: This application allows users to fetch data from Salesforce REST API,
# handle pagination, and display the results in a DataFrame. Users can upload an
# auth.json file for authentication, specify the REST API endpoint, and choose
# whether to fetch all pages of data. The application also provides options to
# download the data as CSV and view the JSON response.
#------------------------------------------------------

def load_auth_credentials(auth_file):
    """
    Loads Salesforce credentials from an auth.json file.

    :param auth_file: Uploaded auth.json file
    :return: Dictionary containing access_token and instance_url
    """
    auth_data = json.load(auth_file)

    # Extract the correct keys for access token and instance URL
    access_token = auth_data.get('access_token') or auth_data.get('accessToken')
    instance_url = auth_data.get('instance_url') or auth_data.get('instanceUrl')

    if not access_token or not instance_url:
        raise ValueError("Missing required credentials in auth.json")

    return {
        'access_token': access_token,
        'instance_url': instance_url
    }


def determine_record_key(endpoint_path, response_json):
    """
    Determines the key to use for accessing records based on the REST API endpoint.

    :param endpoint_path: The REST API endpoint path
    :param response_json: The JSON response from the API
    :return: The key to use for accessing records
    """
    endpoint_key = endpoint_path.split('/')[-1]
    if endpoint_key in response_json:
        return endpoint_key
    # Fallback to the first available key if not found
    return next(iter(response_json.keys()), 'records')

def fetch_data(full_url, headers, instance_url, endpoint_path, all_pages):
    """
    Fetches data from a REST API and handles pagination if necessary.

    :param full_url: The full API endpoint URL
    :param headers: HTTP headers for the API request
    :param instance_url: The base instance URL to resolve pagination links
    :param endpoint_path: The REST API endpoint path to determine record key
    :param all_pages: Boolean flag to indicate whether to fetch all pages
    :return: Tuple of a list of aggregated results and the last page response JSON
    """
    all_records = []
    while full_url:
        response = requests.get(full_url, headers=headers)
        
        if response.status_code != 200:
            st.error(f"Failed to fetch data: {response.status_code} {response.text}")
            return None, None
        
        last_response = response.json()
        # Determine the correct key to use for records
        record_key = determine_record_key(endpoint_path, last_response)
        all_records.extend(last_response.get(record_key, []))
        
        # Check for the next page URL if all_pages is True
        if all_pages:
            full_url = last_response.get('nextPageUrl', None)
            if full_url:
                full_url = urljoin(instance_url, full_url)
        else:
            break
    
    return all_records, last_response

def main():
    st.title("Salesforce REST API Data Fetcher")

    st.sidebar.header("Help Information")
    st.sidebar.write("""
    **To get `auth.json`:**
    1. Login into your org using:
       ```bash
       sf force auth web login -r https://login.salesforce.com
       ```
       or for sandboxes:
       ```bash
       sf force auth web login -r https://test.salesforce.com
       ```
       You will receive the username that got logged into this org in the console/terminal.

    2. Run this command to get `auth.json`:
       ```bash
       sf mohanc hello myorg -u username > auth.json
       ```
    """)

    # Upload auth.json file
    auth_json = st.file_uploader("Upload auth.json file", type=['json'])
    
    if auth_json is not None:
        # Load Salesforce credentials from auth.json
        auth_credentials = load_auth_credentials(auth_json)
        instance_url = auth_credentials['instance_url'].strip()
        
        # Ensure instance_url has the correct scheme
        if not instance_url.startswith(('http://', 'https://')):
            instance_url = 'https://' + instance_url

        # Input field for REST API endpoint path
        endpoint_path = st.text_input("Enter the REST API endpoint path (e.g., /services/data/v60.0/wave/recipes)", '/services/data/v60.0/wave/recipes')
        
        # Option to fetch all pages
        all_pages = st.checkbox("Fetch all pages")

        if st.button("Fetch Data"):
            if not endpoint_path:
                st.error("REST API endpoint path is required.")
                return
            
            # Form the full API URL
            full_url = urljoin(instance_url, endpoint_path)
            
            # Set up headers for the API request
            headers = {
                'Authorization': f'Bearer {auth_credentials["access_token"]}',
                'Content-Type': 'application/json'
            }
            
            try:
                # Fetch data from the API
                data, last_response = fetch_data(full_url, headers, instance_url, endpoint_path, all_pages)
                
                if data is None:
                    return
                
                # Convert the data to a DataFrame if not empty
                if data:
                    df = pd.DataFrame(data)
                    
                    # Display the DataFrame
                    st.dataframe(df)
                    
                    # Save the DataFrame to a CSV file
                    csv = df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name='salesforce_data.csv',
                        mime='text/csv'
                    )
                    
                    # Show the formed API URL
                    st.write("**Formed API URL:**")
                    st.code(full_url)
                    
                    # Show the JSON response if available
                    if last_response:
                        st.write("**JSON Response:**")
                        st.json(last_response)
                
                else:
                    st.warning("No data found.")
            
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()