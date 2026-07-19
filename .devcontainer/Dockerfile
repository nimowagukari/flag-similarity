FROM python:3.12-slim

# git, ca-certificates, curl: 依存取得・Claude Codeインストールに必要
# gh: GitHub CLI（PR操作等）, tmux: 長時間ジョブ・複数ペイン作業用
# jq: JSON整形・各種API応答のパース用
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    git \
    ca-certificates \
    curl \
    gh \
    tmux \
    jq \
    && rm -rf /var/lib/apt/lists/*

# devcontainer標準のnon-rootユーザー
RUN useradd --create-home --shell /bin/bash vscode

RUN mkdir -p /workspaces/flag-similarity && chown vscode:vscode /workspaces/flag-similarity

# ~/.claude を名前付きボリュームで永続化するため、事前にvscode所有で作成しておく
# (ボリューム初回マウント時、イメージ側の内容・所有権がそのままコピーされる)
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude

USER vscode
WORKDIR /workspaces/flag-similarity

# Claude Code CLI (Node不要のネイティブバイナリ版インストーラ)
RUN curl -fsSL https://claude.ai/install.sh | bash

# uv (Pythonライブラリ管理。requirements.txtではなくpyproject.toml/uv.lockを使う)
# バージョンはDockerfile/ci.ymlと合わせる
RUN curl -fsSL https://astral.sh/uv/0.11.29/install.sh | sh

ENV PATH="/home/vscode/.local/bin:${PATH}"
