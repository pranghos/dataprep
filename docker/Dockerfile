FROM ibmfunctions/action-python-v3.7

RUN apt-get install -qy python3
RUN apt-get update 
RUN apt-get install -y python3-pip
RUN apt-get install -y firefox-esr
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
RUN tar -xvzf geckodriver*
RUN chmod +x geckodriver
RUN mv geckodriver /usr/local/bin/
RUN export PATH=$PATH:/usr/local/bin/

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt



ADD . /myapp
COPY . /myapp
WORKDIR /myapp

VOLUME  ./data/Covid_FAQ_v5.xlsx:/myapp/
