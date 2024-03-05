import requests

from helpers.parameters import (
    load_config
)

notion_creds = load_config("creds.yml")
API_URI = "https://api.notion.com/v1"
NOTION_TOKEN = notion_creds['notion']['secret_key']
DATABASE_ID = notion_creds['notion']['database_id']

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def create_page(page_properties: dict):
    create_url = f"{API_URI}/pages"
    payload = {"parent": {"database_id": DATABASE_ID}, "properties": page_properties}
    res = requests.post(create_url, headers=headers, json=payload)
    try:
        json_response = res.json()
        return json_response
    except requests.exceptions.JSONDecodeError as ex:
        print(f'response error {ex}-{res}')


def update_page(page_id: str, page_properties: dict):
    url = f"{API_URI}/pages/{page_id}"
    payload = {"properties": page_properties}
    res = requests.patch(url, json=payload, headers=headers)
    try:
        json_response = res.json()
        return json_response
    except requests.exceptions.JSONDecodeError as ex:
        print(f'response error {ex}-{res}')


def database_filter(payload: dict):
    url = f"{API_URI}/databases/{DATABASE_ID}/query"
    res = requests.post(url, json=payload, headers=headers)
    try:
        json_response = res.json()
        if json_response.get('results') is not None:
            return json_response['results']
        else:
            raise Exception(f'Notion database {DATABASE_ID} not found')
    except requests.exceptions.JSONDecodeError as ex:
        print(f'response error {ex}-{res}')


def get_pages(num_pages=None):
    """
    If num_pages is None, get all pages, otherwise just the defined number.
    """
    url = f"{API_URI}/databases/{DATABASE_ID}/query"
    get_all = num_pages is None
    page_size = 1000 if get_all else num_pages

    payload = {"page_size": page_size}
    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()
    results = response_data["results"]
    while response_data["has_more"] and get_all:
        payload = {"page_size": page_size, "start_cursor": response_data["next_cursor"]}
        url = f"{API_URI}databases/{DATABASE_ID}/query"
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        results.extend(response_data["results"])
    return results
