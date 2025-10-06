# 1. പൈത്തൺ ബേസ് ഇമേജ് ഉപയോഗിക്കുന്നു
FROM python:3.9-slim

# 2. Google Chrome-ഉം Chromedriver-ഉം ഇൻസ്റ്റാൾ ചെയ്യാൻ ആവശ്യമായ കാര്യങ്ങൾ സെറ്റ് ചെയ്യുന്നു
RUN apt-get update && apt-get install -y wget unzip --no-install-recommends

# 3. Google Chrome-ന്റെ ഏറ്റവും പുതിയ പതിപ്പ് ഡൗൺലോഡ് ചെയ്ത് ഇൻസ്റ്റാൾ ചെയ്യുന്നു
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb

# 4. Chromedriver ഡൗൺലോഡ് ചെയ്ത് ഇൻസ്റ്റാൾ ചെയ്യുന്നു (പുതിയ പതിപ്പുകൾക്കനുസരിച്ച് ലിങ്ക് മാറാം)
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chromedriver-linux64.zip
RUN unzip /tmp/chromedriver.zip -d /usr/local/bin/
RUN rm /tmp/chromedriver.zip

# 5. ആപ്ലിക്കേഷൻ കോഡ് കോപ്പി ചെയ്യുന്നു
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

# 6. ആപ്ലിക്കേഷൻ പ്രവർത്തിപ്പിക്കാനുള്ള കമാൻഡ്
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
