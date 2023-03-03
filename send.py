from typing import List, Tuple

import mf2py
import requests
from indieweb_utils import send_webmention

SUPPORTED_TYPES = [
    "h-entry",
]

EXPANDED_SUPPORTED_TYPES = [
    "h-review",
    "h-event",
    "h-recipe",
    "h-resume",
    "h-product",
    "h-cite",
]


def _check_supported_type(parsed_mf2_tree: dict, supported_types: list) -> bool:
    """
    Check if the parsed mf2 tree contains a supported type.

    :param parsed_mf2_tree: The parsed mf2 tree.
    :type parsed_mf2_tree: dict
    :param supported_types: The supported types.
    :type supported_types: list
    :returns: True if the parsed mf2 tree contains a supported type, False otherwise.
    :rtype: bool
    """
    if parsed_mf2_tree.get("type", [])[0] in supported_types:
        return True

    return False


def _get_nested_h_entry(parsed_mf2_tree: dict, supported_types: list) -> List[dict]:
    """
    Get the nested h-* objects from a parsed mf2 tree.

    :param parsed_mf2_tree: The parsed mf2 tree.
    :type parsed_mf2_tree: dict
    :param supported_types: The supported types.
    :type supported_types: list
    :returns: The nested h-* objects.
    :rtype: dict
    """
    nested_entry = []

    for entry in parsed_mf2_tree.get("items"):
        if _check_supported_type(entry, supported_types):
            for nested in entry.get("children", []):
                if _check_supported_type(nested, supported_types):
                    nested_entry.extend(nested)
                    break

                if nested.get("type") == ["h-feed"]:
                    nested_entry.extend(_recursively_get_entries_from_nested_entry(
                        nested.get("children"), supported_types
                    ))
                    if nested_entry == None:
                        nested_entry = []
                        continue

                    break

    return nested_entry


def _recursively_get_entries_from_nested_entry(
    nested_entry: dict, supported_types: list
) -> List[dict]:
    """
    Recursively get all entries from a nested entry.

    :param nested_entry: The nested entry.
    :type nested_entry: dict
    :param supported_types: The supported types.
    :type supported_types: list
    :returns: The entries.
    :rtype: List[dict]
    """

    entries = []

    for entry in nested_entry:
        if _check_supported_type(entry, supported_types):
            entries.append(entry)
            print('e')

        if entry.get("type") == ["h-feed"]:
            entries.extend(
                _recursively_get_entries_from_nested_entry(
                    entry.get("children"), supported_types
                )
            )

    return entries


def receive_salmention(
    current_page_contents: str,
    original_post_contents: str,
    supported_types: list = SUPPORTED_TYPES,
) -> Tuple[List[dict], List[str], List[str]]:
    """
    Process a Salmention. Call this function only when you receive a Webmention
    to a page that has already received a Webmention.

    :param url: The URL of the page that received the Webmention.
    :type url: str
    :param original_post_contents: The HTML contents of the original post.
    :type original_post_contents: str
    :param current_page_contents: The HTML contents of the current page.
    :type current_page_contents: str
    :returns: The new nested responses, the URLs of the webmentions sent, and the URLs of the deleted posts.
    :rtype: Tuple[List[dict], List[str], List[str]]

    Example:

    .. code-block:: python

        from indieweb_utils import receive_salmention

        receive_salmention('<html>...</html>', '<html>...</html>')
    """

    new_parsed_mf2_tree = mf2py.parse(current_page_contents)
    new_nested_entry = _get_nested_h_entry(new_parsed_mf2_tree, supported_types)

    original_parsed_mf2_tree = mf2py.parse(original_post_contents)
    original_nested_entry = _get_nested_h_entry(
        original_parsed_mf2_tree, supported_types
    )

    # return new nested responses
    new_nested_responses = []

    all_original_urls = [
        x["properties"].get("url", [])[0] for x in original_nested_entry
    ]

    all_new_urls = [x["properties"].get("url", [])[0] for x in new_nested_entry]

    deleted_posts = [x for x in all_new_urls if x not in all_original_urls]

    # remove empty items
    deleted_posts = [x for x in deleted_posts if x]

    if not original_nested_entry:
        return new_nested_responses, [], deleted_posts

    urls_webmentions_sent = {"success": [], "failed": []}

    # for all nested urls, send webmentions
    for response in original_nested_entry:
        # and url not in all_new_urls
        if response["properties"].get("url"):
            post_url = response["properties"].get("url")[0]
            try:
                send_webmention(response["properties"].get("url")[0], post_url)
                urls_webmentions_sent["success"].append(post_url)
            except:
                urls_webmentions_sent["failed"].append(post_url)

            if response["properties"]["url"][0] not in all_new_urls:
                new_nested_responses.append(response)

    return new_nested_responses, urls_webmentions_sent, deleted_posts

if __name__ == "__main__":
    with open("site_reply_to_jamesgblog.html") as file:
        site_reply_to_jamesgblog = file.read()

    with open("reply_to_reply.html") as file:
        reply_to_reply = file.read()

    with open("jamesgblog.html") as file:
        jamesgblog = file.read()

    new, sent, deleted = receive_salmention(reply_to_reply, site_reply_to_jamesgblog)

    print("new", new)
    print("sent", sent)
    print("deleted", deleted)
