FROM python:3.12-slim

# bubblewrap, socat: Claude Codeのネイティブサンドボックス(bwrap+socatプロキシ)に必須
# git, ca-certificates, curl: 依存取得・Claude Codeインストールに必要
# gh: GitHub CLI（PR操作等）, tmux: 長時間ジョブ・複数ペイン作業用
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    git \
    ca-certificates \
    curl \
    gh \
    tmux \
    iptables \
    ipset \
    iproute2 \
    dnsutils \
    aggregate \
    jq \
    && rm -rf /var/lib/apt/lists/*

# devcontainer標準のnon-rootユーザー
RUN useradd --create-home --shell /bin/bash vscode

RUN mkdir -p /workspaces/flag-similarity && chown vscode:vscode /workspaces/flag-similarity

# Copy and set up firewall script
COPY init-firewall.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/init-firewall.sh && \
  echo "vscode ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/vscode-firewall && \
  chmod 0440 /etc/sudoers.d/vscode-firewall



USER vscode
WORKDIR /workspaces/flag-similarity

# Claude Code CLI (Node不要のネイティブバイナリ版インストーラ)
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/home/vscode/.local/bin:${PATH}"
