"""
Safe mouse handler for Playwright automation to prevent accidental UI interactions.
"""

from playwright.async_api import Page
import asyncio


class SafeMouseHandler:
    """Handles mouse movements and clicks safely to prevent accidental UI interactions."""
    
    def __init__(self, page: Page):
        self.page = page
        self.safe_zones = [
            {'x': 50, 'y': 50},    # Top-left safe zone
            {'x': 100, 'y': 100},  # Alternative safe zone
            {'x': 10, 'y': 10},    # Minimal safe zone
        ]
        self.current_safe_zone = 0
    
    async def move_to_safe_zone(self):
        """Move mouse to a safe area to prevent hover states."""
        try:
            safe_zone = self.safe_zones[self.current_safe_zone]
            await self.page.mouse.move(safe_zone['x'], safe_zone['y'])
            await self.page.wait_for_timeout(100)
            
            # Rotate to next safe zone for variety
            self.current_safe_zone = (self.current_safe_zone + 1) % len(self.safe_zones)
        except Exception:
            # Fallback to basic coordinates
            await self.page.mouse.move(50, 50)
    
    async def safe_click(self, selector: str, **kwargs):
        """Perform a safe click that dismisses overlays first."""
        try:
            # Move to safe zone first
            await self.move_to_safe_zone()
            await self.page.wait_for_timeout(200)
            
            # Press Escape to dismiss any overlays
            await self.page.keyboard.press('Escape')
            await self.page.wait_for_timeout(100)
            
            # Perform the click
            await self.page.click(selector, **kwargs)
            
            # Move back to safe zone after click
            await self.move_to_safe_zone()
            
        except Exception as e:
            # If safe click fails, try regular click as fallback
            await self.page.click(selector, **kwargs)
    
    async def safe_hover(self, selector: str):
        """Perform a safe hover that moves away afterwards."""
        try:
            # Hover on element
            await self.page.hover(selector)
            await self.page.wait_for_timeout(100)
            
            # Move away to safe zone
            await self.move_to_safe_zone()
            
        except Exception:
            # If hover fails, just move to safe zone
            await self.move_to_safe_zone()
    
    async def prevent_context_menu(self):
        """Prevent context menus from appearing by handling right-clicks."""
        try:
            # Add JavaScript to prevent context menus
            await self.page.evaluate("""
                document.addEventListener('contextmenu', function(e) {
                    e.preventDefault();
                    return false;
                }, true);
            """)
        except Exception:
            pass
    
    async def dismiss_all_overlays(self):
        """Comprehensive overlay dismissal."""
        try:
            # Press Escape multiple times
            for _ in range(3):
                await self.page.keyboard.press('Escape')
                await self.page.wait_for_timeout(100)
            
            # Click in safe area
            await self.page.click('body', position={'x': 10, 'y': 10})
            await self.page.wait_for_timeout(200)
            
            # Move to safe zone
            await self.move_to_safe_zone()
            
        except Exception:
            pass