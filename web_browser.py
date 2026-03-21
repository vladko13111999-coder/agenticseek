import logging
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class WebBrowser:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
    
    def start(self):
        if self.playwright is None:
            self.playwright = sync_playwright().start()
        if self.browser is None:
            self.browser = self.playwright.chromium.launch(headless=True)
        if self.context is None:
            self.context = self.browser.new_context()
        return True
    
    def browse(self, url: str, wait_seconds: int = 3) -> Dict[str, Any]:
        try:
            self.start()
            page = self.context.new_page()
            
            logger.info(f"Browsing: {url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_seconds * 1000)
            
            title = page.title()
            content = page.content()
            
            text_content = page.inner_text("body")
            
            page.close()
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "text": text_content[:5000],
                "full_html": content[:10000]
            }
            
        except Exception as e:
            logger.error(f"Browser error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_page(self, url: str) -> Dict[str, Any]:
        result = self.browse(url, wait_seconds=3)
        
        if not result.get("success"):
            return result
        
        text = result.get("text", "")
        
        return {
            "success": True,
            "url": url,
            "title": result.get("title", ""),
            "content_preview": text[:2000],
            "message": f"Stránka {url} bola úspešne načítaná.\\n\\nTitulok: {result.get('title', 'N/A')}\\n\\nObsah:\\n{text[:1500]}..."
        }

web_browser = WebBrowser()

def analyze_website(url: str) -> Dict[str, Any]:
    try:
        return web_browser.analyze_page(url)
    except Exception as e:
        logger.error(f"Website analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Pri analýze webovej stránky došlo k chybe."
        }
