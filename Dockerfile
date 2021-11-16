FROM juniper/pyez

RUN pip install -U pip
RUN pip install ansible
RUN pip install colorama

COPY . .
ENTRYPOINT python3 network_triage.py
