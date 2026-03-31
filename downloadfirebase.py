import os
import re
import requests
import urllib.parse

# ==============================
# CONFIGURATION (EDIT THESE)
# ==============================

vaultDir = '/path/to/your/obsidian/vault'   # ← change this
assetsFolderName = 'Assets'          # ← change if needed

# ==============================

assetsDir = os.path.join(vaultDir, assetsFolderName)
os.makedirs(assetsDir, exist_ok=True)

# --- REGEX PATTERNS ---

# Images with optional size: ![|300x200](URL)
img_pattern = re.compile(r'!\[\|?([0-9x]*)\]\((https://firebasestorage[^\)]+)\)')

# PDFs: {{pdf: URL}} OR {{[[pdf]]: URL}}
pdf_pattern = re.compile(r'\{\{\s*(?:\[\[pdf\]\]|pdf)\s*:\s*(https://firebasestorage[^\}]+)\}\}')

# Any remaining Firebase links
raw_pattern = re.compile(r'(https://firebasestorage[^\s\)\}]+)')


# --- EXTRACT FILENAME FROM FIREBASE URL ---
def get_filename_from_url(url):
    try:
        path = re.search(r'/o/(.*?)\?', url).group(1)
        decoded = urllib.parse.unquote(path)
        return os.path.basename(decoded)
    except:
        return "file.bin"


# --- DOWNLOAD FILE ---
def download_file(url):
    try:
        r = requests.get(url, stream=True, timeout=10)
        if r.status_code != 200:
            print("❌ Failed:", url)
            return None

        filename = get_filename_from_url(url)
        local_path = os.path.join(assetsDir, filename)

        # Avoid overwriting existing files
        base, ext = os.path.splitext(filename)
        i = 1
        while os.path.exists(local_path):
            local_path = os.path.join(assetsDir, f"{base}_{i}{ext}")
            i += 1

        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        return os.path.basename(local_path)

    except Exception as e:
        print("⚠️ Error:", url, e)
        return None


# --- MAIN PROCESS ---

for root, _, files in os.walk(vaultDir):
    for fname in files:

        file_path = os.path.join(root, fname)

        # Skip attachments folder to avoid reprocessing
        if assetsFolderName in file_path:
            continue

        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue

        original_content = content

        # --- IMAGES ---
        for match in img_pattern.finditer(content):
            size, url = match.groups()

            filename = download_file(url)
            if not filename:
                continue

            new_link = f"![[{assetsFolderName}/{filename}"
            if size:
                new_link += f"|{size}"
            new_link += "]]"

            content = content.replace(match.group(0), new_link)

        # --- PDFs ---
        for match in pdf_pattern.finditer(content):
            url = match.group(1)

            filename = download_file(url)
            if not filename:
                continue

            new_link = f"![[{assetsFolderName}/{filename}]]"
            content = content.replace(match.group(0), new_link)

        # --- RAW LINKS (fallback) ---
        for url in raw_pattern.findall(content):
            if url not in content:
                continue

            filename = download_file(url)
            if not filename:
                continue

            new_link = f"![[{assetsFolderName}/{filename}]]"
            content = content.replace(url, new_link)

        # --- SAVE FILE IF MODIFIED ---
        if content != original_content:
            print("Updated:", file_path)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

print("\n✅ Done.")
