import mf2py
from typing import List, Tuple

from indieweb_utils import send_webmention

SUPPORTED_TYPES = ["h-entry", "h-review", "h-event", "h-recipe", "h-resume", "h-product", "h-cite"]

def _get_nested_h_entry(parsed_mf2_tree: dict) -> List[dict]:
    """
    Get the nested h-* objects from a parsed mf2 tree.

    :param parsed_mf2_tree: The parsed mf2 tree.
    :type parsed_mf2_tree: dict
    :returns: The nested h-* objects.
    :rtype: dict
    """
    nested_entry = []

    for entry in parsed_mf2_tree.get("items"):
        if entry.get("type", [])[0] in SUPPORTED_TYPES:
            for nested_entry in entry.get("children", []):
                if nested_entry.get("type", [])[0] in SUPPORTED_TYPES:
                    nested_entry = [nested_entry]
                    break

                if nested_entry.get("type") == ["h-feed"]:
                    nested_entry = _recursively_get_entries_from_nested_entry(nested_entry.get("children"))
                    if nested_entry == None:
                        nested_entry = []
                        continue
                    
                    break

        if nested_entry != {}:
            break

    return nested_entry

def _recursively_get_entries_from_nested_entry(nested_entry: dict) -> List[dict]:
    """
    Recursively get all entries from a nested entry.

    :param nested_entry: The nested entry.
    :type nested_entry: dict
    :returns: The entries.
    :rtype: List[dict]
    """

    entries = []

    for entry in nested_entry:
        if entry.get("type", [])[0] in SUPPORTED_TYPES:
            entries.append(entry)

        if entry.get("type") == ["h-feed"]:
            entries.extend(_recursively_get_entries_from_nested_entry(entry.get("children")))

    return entries

def receive_salmention(current_page_contents: str, original_post_contents: str) -> Tuple[List[dict], List[str], List[str]]:
    """
    Process a Salmention. Call this function only when you receive a Webmention
    to a page that has already received a Webmention.

    :param url: The URL of the page that received the Webmention.
    :type url: str
    :param original_post_contents: The HTML contents of the original post.
    :type original_post_contents: str
    :returns: The new nested responses, the URLs of the webmentions sent, and the URLs of the deleted posts.
    :rtype: Tuple[List[dict], List[str], List[str]]

    Example:

    .. code-block:: python

        from indieweb_utils import receive_salmention

        receive_salmention('http://example.com/post/123', '<html>...</html>')
    """

    new_parsed_mf2_tree = mf2py.parse(current_page_contents)
    new_nested_entry = _get_nested_h_entry(new_parsed_mf2_tree)

    original_parsed_mf2_tree = mf2py.parse(original_post_contents)
    original_nested_entry = _get_nested_h_entry(original_parsed_mf2_tree)

    # return new nested responses
    new_nested_responses = []

    all_original_urls = [x["properties"].get("url", [])[0] for x in original_nested_entry]
    all_new_urls = [x["properties"].get("url", [])[0] for x in new_nested_entry]

    deleted_posts = [x for x in all_new_urls if x not in all_original_urls]

    # remove empty items
    deleted_posts = [x for x in deleted_posts if x]

    if not original_nested_entry:
        return new_nested_responses, [], deleted_posts

    urls_webmentions_sent = {"success": [], "failed": []}

    # for all nested urls, send webmentions
    for response in original_nested_entry:
        if response["properties"].get("url"):
            post_url = response["properties"].get("url")[0]
            try:
                send_webmention(response["properties"].get("url")[0], "https://aaronparecki.com")
                urls_webmentions_sent["success"].append(post_url)
            except:
                urls_webmentions_sent["failed"].append(post_url)

            new_nested_responses.append(response)

    return new_nested_responses, urls_webmentions_sent, deleted_posts

with open("new.html", "r") as f:
    contents = f.read()

new, sent, deleted = receive_salmention("", contents)

print("new", new)
print("sent", sent)
print("deleted", deleted)