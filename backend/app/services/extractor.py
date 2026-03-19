import re
from bs4 import BeautifulSoup, Comment

def extract_main_text(html: str, max_length: int = 5000) -> str:
    """Extract readable text from HTML, stripping boilerplate."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove unwanted tags
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe']):
        element.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Find main content if possible
    main = soup.find('main') or soup.find('article') or soup.find(id=re.compile(r'content|main')) or soup
    
    text = main.get_text(separator=' ', strip=True)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate to save context
    if len(text) > max_length:
        text = text[:max_length] + "..."
        
    return text
