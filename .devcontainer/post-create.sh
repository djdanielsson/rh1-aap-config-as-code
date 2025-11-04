#!/bin/bash
# Post-create script for aap-config-as-code development container
# This script runs after the container is created

set -e

echo "🚀 Setting up AAP Config as Code development environment..."

# Install/upgrade development tools
echo "📦 Installing development tools..."

# Ensure pip is up to date
pip install --upgrade pip

# Install Ansible and related tools
pip install \
    ansible-core>=2.15 \
    ansible-lint \
    ansible-navigator \
    yamllint \
    jinja2-cli \
    pre-commit \
    detect-secrets \
    molecule \
    molecule-plugins[docker] \
    pytest \
    pytest-ansible

# Install Ansible collections
echo "📚 Installing Ansible collections..."
ansible-galaxy collection install -r collections/requirements.yml --force

# Install yq (YAML processor)
VERSION=v4.40.5
BINARY=yq_linux_amd64
wget -q https://github.com/mikefarah/yq/releases/download/${VERSION}/${BINARY} -O /tmp/yq
mv /tmp/yq /usr/local/bin/yq
chmod +x /usr/local/bin/yq

# Setup pre-commit
if [ -f .pre-commit-config.yaml ]; then
    echo "🔧 Installing pre-commit hooks..."
    pre-commit install
    pre-commit install --hook-type commit-msg
fi

# Git configuration
echo "⚙️  Configuring Git..."
git config --global --add safe.directory /workspace

# Create helpful aliases
echo "📝 Setting up shell aliases..."
cat >> ~/.bashrc <<'EOF'

# Ansible Aliases
alias ap='ansible-playbook'
alias apv='ansible-playbook --syntax-check'
alias apc='ansible-playbook --check'
alias apd='ansible-playbook --check --diff'
alias al='ansible-lint'
alias an='ansible-navigator'
alias ag='ansible-galaxy'
alias av='ansible-vault'

# Validation Aliases
alias lint-all='yamllint . && ansible-lint'
alias syntax-check='ansible-playbook playbook.yml --syntax-check'
alias validate-inventory='ansible-inventory -i inventory.yml --list'
alias dry-run='ansible-playbook playbook.yml --check --diff'

# Git Aliases
alias gs='git status'
alias gp='git pull'
alias gc='git commit'
alias gco='git checkout'

# AAP Config Helpers
alias test-dev='ansible-playbook playbook.yml --limit aap_dev --check'
alias test-qa='ansible-playbook playbook.yml --limit aap_qa --check'
alias test-prod='ansible-playbook playbook.yml --limit aap_prod --check'
EOF

source ~/.bashrc

# Create ansible.cfg if it doesn't exist
if [ ! -f ansible.cfg ]; then
    echo "📝 Creating ansible.cfg..."
    cat > ansible.cfg <<'EOF'
[defaults]
inventory = inventory.yml
roles_path = ~/.ansible/roles:/usr/share/ansible/roles
collections_path = ~/.ansible/collections:/usr/share/ansible/collections
host_key_checking = False
retry_files_enabled = False
stdout_callback = yaml
bin_ansible_callbacks = True
deprecation_warnings = False

[inventory]
enable_plugins = yaml, ini

[privilege_escalation]
become = False
EOF
fi

echo "✅ AAP Config as Code development environment ready!"
echo ""
echo "Available commands:"
echo "  - ansible, ansible-playbook, ansible-lint"
echo "  - ansible-navigator (execution environment runner)"
echo "  - ansible-vault (secret management)"
echo "  - yamllint, pre-commit"
echo "  - yq (YAML processor)"
echo ""
echo "Quick commands:"
echo "  - lint-all: Run yamllint and ansible-lint"
echo "  - syntax-check: Validate playbook syntax"
echo "  - dry-run: Test playbook without making changes"
echo "  - test-dev/qa/prod: Test specific environment"

