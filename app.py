import os
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    
    # Render-ൽ ഈ ഭാഗം ആവശ്യമില്ല, കാരണം Dockerfile പാത്ത് ശരിയാക്കും
    # chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

@app.route('/', methods=['GET'])
def scrape_gdflix():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({"success": False, "error": "URL parameter required"}), 400

    driver = None
    try:
        driver = setup_driver()
        driver.get(target_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Instant DL"))
        )

        file_name = driver.find_element(By.TAG_NAME, "h3").text.strip()
        
        file_size = "Unknown"
        list_items = driver.find_elements(By.CLASS_NAME, "list-group-item")
        for item in list_items:
            if "Size" in item.text:
                file_size = item.text.split(":")[1].strip()
                break
        
        downloads = []
        links = driver.find_elements(By.CSS_SELECTOR, "a.btn")
        for link in links:
            text = link.text.strip().lower()
            if "g-drive" in text or "copy all" in text or "login" in text:
                continue
            downloads.append({
                "server": link.text.strip(),
                "url": link.get_attribute('href')
            })

        return jsonify({
            "success": True, "type": "file", "fileName": file_name,
            "fileSize": file_size, "totalServers": len(downloads), "downloads": downloads
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    app.run()
