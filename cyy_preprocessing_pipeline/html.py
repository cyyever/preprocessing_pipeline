import bs4


def parsing_html_tag(html: str, prefered_tag: str | None = None) -> str:
    # Parse HTML using BeautifulSoup
    soup = bs4.BeautifulSoup(html, "html.parser")
    result = ""
    for child in soup:
        match child:
            case bs4.element.NavigableString():
                result += child.get_text()
            case bs4.element.Tag():
                last_tag_text = child.get_text()
                tag_name = child.name.lower()
                if prefered_tag is not None and tag_name == prefered_tag.lower():
                    return child.get_text()
                result += f"<{tag_name}>{last_tag_text}</{tag_name}>"
            case _:
                raise NotImplementedError(child)
    return result
