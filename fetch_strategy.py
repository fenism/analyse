
import sys
import os
from pathlib import Path
import time
import re

# Add skill scripts to path
SKILL_DIR = Path.home() / ".agent/skills/notebooklm"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

# Import from skill scripts
from browser_utils import BrowserFactory, StealthUtils
from config import QUERY_INPUT_SELECTORS, RESPONSE_SELECTORS
from patchright.sync_api import sync_playwright

def ask_custom(notebook_url, question):
    playwright = sync_playwright().start()
    try:
        # Use existing browser profile from skill
        context = BrowserFactory.launch_persistent_context(playwright, headless=True)
        page = context.new_page()
        
        print(f"Opening {notebook_url}...")
        page.goto(notebook_url, wait_until="domcontentloaded")
        
        # INCREASED TIMEOUT HERE to 60s
        print("Waiting for page load...")
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=60000)
        
        # Wait for input
        print("Waiting for input selector...")
        query_element = None
        for selector in QUERY_INPUT_SELECTORS:
            try:
                query_element = page.wait_for_selector(selector, state="visible", timeout=30000)
                if query_element: 
                    print(f"Found selector: {selector}")
                    break
            except: 
                continue
            
        if not query_element:
            print("Input not found")
            return

        print("Typing question...")
        StealthUtils.human_type(page, QUERY_INPUT_SELECTORS[0], question)
        page.keyboard.press("Enter")
        
        # Wait for answer
        print("Waiting for answer...")
        answer = None
        deadline = time.time() + 180 # 3 mins timeout
        last_text = ""
        stable_count = 0
        
        while time.time() < deadline:
            # Check response
            found_any = False
            for selector in RESPONSE_SELECTORS:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        found_any = True
                        latest = elements[-1]
                        text = latest.inner_text().strip()
                        
                        # Only consider non-empty text that is different from previous (or stabilizing)
                        if text:
                            if text == last_text:
                                stable_count += 1
                                if stable_count >= 5: # Stable for 5 seconds
                                    answer = text
                                    break
                            else:
                                stable_count = 0
                                last_text = text
                except:
                    pass
            
            if answer: 
                break
                
            # If still thinking...
            try:
                thinking = page.query_selector('div.thinking-message')
                if thinking and thinking.is_visible():
                    stable_count = 0 # Reset stability if thinking
            except: pass
            
            time.sleep(1)
            
        if answer:
            print("\n--- ANSWER ---")
            print(answer)
            print("--------------")
        else:
            print("Timeout waiting for answer.")
            
    finally:
        try: context.close()
        except: pass
        try: playwright.stop()
        except: pass

if __name__ == "__main__":
    url = "https://notebooklm.google.com/notebook/fd11568a-4cab-4f5b-aba9-6a5f6eee6231"
    q = "请详细提供以下策略的精确Python实现逻辑、数学公式和参数设置：\n1. Fighting/DTR Plus (MACD条件, '翻红'定义)\n2. CYC MAX (无穷成本均线计算公式, 如何用OHLCV模拟)\n3. HLP3 (获利盘比例计算公式)\n4. Limit (成交量缩量比例, N天数)\n5. Zero-Profit (阈值)\n6. Rank 评分模型细节\n如果原文没有精确公式，请根据上下文给出最佳近似算法。"
    ask_custom(url, q)
