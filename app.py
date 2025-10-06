import os
import time
import re
from functools import wraps
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

app = Flask(__name__)

# Configuration
MAX_REQUESTS_PER_MINUTE = 60
REQUEST_TIMEOUT = 30

# Simple rate limiting (Note: In-memory, resets on server restart)
request_counts = {}

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_minute = int(time.time() / 60)
        key = f"{ip}:{current_minute}"
        
        request_counts[key] = request_counts.get(key, 0) + 1
        
        if request_counts[key] > MAX_REQUESTS_PER_MINUTE:
            return jsonify({
                'success': False,
                'error': f'Rate limit exceeded: {MAX_REQUESTS_PER_MINUTE} req/min'
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function

def setup_driver():
    """Setup Chrome driver with optimal settings"""
    chrome_options = Options()
    
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(REQUEST_TIMEOUT)
    driver.implicitly_wait(5)
    
    return driver

def extract_file_info(driver):
    """Extract file name and size from page"""
    file_name, file_size = "Unknown", "Unknown"
    
    try:
        selectors = ['h1', 'h2', 'h3', '.card-title', '.file-name']
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.text.strip():
                    file_name = element.text.strip()
                    break
            except NoSuchElementException:
                continue
    except Exception as e:
        print(f"Error extracting file name: {e}")
    
    try:
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        # --- FIX: Corrected the regex pattern ---
        size_match = re.search(r'([\d.]+\s*(?:GB|MB|TB))', page_text, re.IGNORECASE)
        if size_match:
            file_size = size_match.group(1)
    except Exception as e:
        print(f"Error extracting file size: {e}")
    
    return file_name, file_size

def extract_download_links(driver):
    """Extract all download links from page"""
    downloads = []
    
    try:
        # Wait for links to be clickable, a more robust wait
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Download"))
        )
        
        links = driver.find_elements(By.TAG_NAME, 'a')
        
        for link in links:
            try:
                text = link.text.strip()
                href = link.get_attribute('href')
                
                if not text or not href: continue
                
                text_lower = text.lower()
                skip_keywords = ['login', 'home', 'copy all', 'g-drive link', 'logout']
                if any(keyword in text_lower for keyword in skip_keywords): continue
                
                server_name = None
                if 'instant' in text_lower: server_name = 'Instant Download [10GBPS]'
                elif 'pixeldrain' in text_lower: server_name = 'PixelDrain [20MB/S]'
                elif 't.me/' in href: server_name = 'Telegram Bot'
                elif 'cloud' in text_lower or 'zipdisk' in text_lower: server_name = 'Fast Cloud / ZipDisk'
                elif 'gofile' in text_lower or 'mirror' in text_lower: server_name = 'GoFile Mirror'
                elif 'download' in text_lower: server_name = text
                
                if server_name:
                    downloads.append({'server': server_name, 'url': href, 'buttonText': text})
            except Exception:
                continue
        
    except Exception as e:
        print(f"Error extracting links: {e}")
    
    return downloads

# --- API Routes ---

@app.route('/')
def home():
    return jsonify({
        'service': 'GDFlix Scraper API', 'version': '2.0.0', 'status': 'online',
        'usage': 'GET /scrape?url=https://gdflix.net/file/ABC123'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/scrape')
@rate_limit
def scrape():
    target_url = request.args.get('url')
    
    if not target_url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400
    
    valid_domains = ['gdflix.', 'gdlink.', 'vifix.', 'goflix.']
    if not any(domain in target_url.lower() for domain in valid_domains):
        return jsonify({'success': False, 'error': 'Only GDFlix-related URLs are supported'}), 400
    
    driver = None
    start_time = time.time()
    
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Scraping: {target_url}")
        
        driver = setup_driver()
        driver.get(target_url)
        
        # --- REMOVED: time.sleep(3) is not reliable ---
        
        file_name, file_size = extract_file_info(driver)
        downloads = extract_download_links(driver)
        
        elapsed = time.time() - start_time
        
        if not downloads:
            raise Exception("No download links found after page load.")

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Success! Found {len(downloads)} links in {elapsed:.2f}s")
        
        return jsonify({
            'success': True, 'type': 'file', 'fileName': file_name, 'fileSize': file_size,
            'totalServers': len(downloads), 'downloads': downloads, 'responseTime': f'{elapsed:.2f}s'
        })
        
    except TimeoutException:
        return jsonify({'success': False, 'error': 'Request timeout. Page took too long to load.'}), 504
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Error closing driver: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
