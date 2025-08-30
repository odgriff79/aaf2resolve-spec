FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Python + Node + common tools
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv nodejs npm git make && \
    rm -rf /var/lib/apt/lists/*

# (Optional) CLIs if you want to experiment locally:
# RUN npm i -g @google/generative-ai-cli@latest
# RUN pip install openai
