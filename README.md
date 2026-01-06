# AAP Configuration-as-Code Repository

**Purpose**: Application GitOps for Ansible Automation Platform  
**Managed By**: Tekton CaC Pipeline  
**Collection**: `infra.aap_configuration`

## Overview

This repository contains declarative configuration for all AAP environments (dev, qa, prod). Changes pushed to this repository are automatically applied via Tekton pipelines.

**Constitution Compliance**: Article II (Application GitOps)

## Repository Structure

```
aap-config-as-code/
├── README.md                       # This file
├── .gitignore                      # Git ignore patterns
├── inventory.yml                   # AAP environment inventory
├── playbook.yml                    # Main CaC playbook (uses dispatch role)
├── collections/
│   └── requirements.yml            # Collection dependencies
├── group_vars/
│   ├── all/                        # Global variables (all environments)
│   │   ├── organizations.yml
│   │   ├── labels.yml
│   │   ├── teams.yml
│   │   └── execution_environments.yml
│   ├── aap_dev/                    # Dev-specific configuration
│   │   ├── execution_environments.yml
│   │   ├── credentials.yml
│   │   ├── projects.yml
│   │   ├── inventories.yml
│   │   ├── hosts.yml
│   │   ├── job_templates.yml
│   │   ├── schedules.yml
│   │   └── settings.yml
│   ├── aap_qa/                     # QA-specific configuration
│   │   ├── execution_environments.yml
│   │   ├── credentials.yml
│   │   ├── projects.yml
│   │   ├── inventories.yml
│   │   ├── hosts.yml
│   │   ├── job_templates.yml
│   │   ├── schedules.yml
│   │   └── settings.yml
│   └── aap_prod/                   # Prod-specific configuration
│       ├── execution_environments.yml
│       ├── credentials.yml
│       ├── projects.yml
│       ├── inventories.yml
│       ├── hosts.yml
│       ├── job_templates.yml
│       ├── workflow_templates.yml
│       ├── schedules.yml
│       ├── notifications.yml
│       └── settings.yml
└── files/
    └── (reserved for future use)

```

## Configuration Model

### Dispatch Role with Wildcard Variables

This repository uses the **dispatch** role from the `infra.aap_configuration` collection ([documentation](https://github.com/redhat-cop/infra.aap_configuration/blob/devel/roles/dispatch/README.md)).

**Key Benefits:**
- ✅ **Automatic ordering**: Handles dependencies (organizations → credentials → projects → job templates)
- ✅ **Wildcard support**: Merge multiple `controller_*_suffix` variables automatically
- ✅ **Better organization**: Split large configurations into logical groups
- ✅ **Simpler playbook**: One `include_role` instead of dozens of role calls
- ✅ **Flexible tagging**: All roles get appropriate tags automatically

**How It Works:**

The playbook uses `dispatch_include_wildcard_vars: true`, which automatically finds and merges variables with patterns like:

```yaml
# These all get merged into controller_job_templates
controller_job_templates_dev:        # Environment-specific base
  - name: Dev Common Template

controller_job_templates_dev_web:    # Wildcard: merged automatically
  - name: Web App Template

controller_job_templates_dev_database:  # Wildcard: merged automatically
  - name: Database Template
```

**Result**: All three lists are combined into `controller_job_templates` and applied together to Dev AAP.

### Why Use Wildcards?

Based on the [casc_demo repository](https://github.com/djdanielsson/casc_demo) pattern, wildcards provide:

1. **Logical Grouping**: Group related resources together
   - `controller_job_templates_dev_web` - All web-related templates in dev
   - `controller_job_templates_dev_database` - All database templates in dev
   - `controller_job_templates_dev_network` - All network templates in dev

2. **Team Ownership**: Different teams can own different files
   - Team A maintains `controller_projects_dev_team_a`
   - Team B maintains `controller_projects_dev_team_b`
   - No merge conflicts!

3. **Environment Layering**: Common + specific configurations
   - `group_vars/all/projects.yml` has `controller_projects_all` (common to all envs)
   - `group_vars/aap_dev/projects.yml` has `controller_projects_dev` (dev-specific)
   - `group_vars/aap_dev/projects.yml` has `controller_projects_dev_platform` (dev platform)
   - All are automatically merged!

4. **Easier Reviews**: Small, focused files are easier to review than monolithic configurations

### Organizing with Wildcard Variables

You can organize configurations by application, team, or purpose:

**Option 1: By Application**
```yaml
# group_vars/aap_dev/projects.yml
controller_projects_dev_platform:
  - name: Platform Automation
    scm_url: https://github.com/org/platform.git

controller_projects_dev_networking:
  - name: Network Automation
    scm_url: https://github.com/org/network.git

# group_vars/aap_dev/job_templates.yml
controller_job_templates_dev_platform:
  - name: Deploy Infrastructure
    project: Platform Automation

controller_job_templates_dev_networking:
  - name: Configure Switches
    project: Network Automation
```

**Option 2: By Team**
```yaml
# group_vars/aap_dev/projects.yml
controller_projects_dev_team_ops:
  - name: Ops Playbooks
    organization: Operations

controller_projects_dev_team_security:
  - name: Security Playbooks
    organization: Security
```

**Option 3: By Environment Layer** (recommended - used in this repo)
```yaml
# group_vars/all/projects.yml (would need to create this file)
controller_projects_all:
  - name: Shared Libraries
    scm_url: https://github.com/org/common.git

# group_vars/aap_dev/projects.yml  
controller_projects_dev:
  - name: Dev-Specific Project
    scm_url: https://github.com/org/dev-app.git

# group_vars/aap_prod/projects.yml
controller_projects_prod:
  - name: Prod-Specific Project
    scm_url: https://github.com/org/prod-app.git
```

### Directory Organization (group_vars/)

Configuration is organized into directories for better maintainability:

**`group_vars/all/`** - Shared across all environments:
- `organizations.yml` - Common organizations (Default, Platform, Applications)
- `labels.yml` - Common labels for organizing resources
- `teams.yml` - Common teams structure
- `execution_environments.yml` - Base execution environment
- `credential_types.yml` - Custom credential types (e.g., HashiCorp Vault)

**`group_vars/aap_dev/`** - Development environment:
- `execution_environments.yml` - Dev EEs (uses `latest` tags, always pull)
- `credentials.yml` - Dev credentials (references to secrets)
- `projects.yml` - Dev projects (uses `develop` branches, auto-update enabled)
- `inventories.yml` - Dev inventories
- `hosts.yml` - Dev inventory hosts
- `job_templates.yml` - Dev job templates (permissive settings)
- `schedules.yml` - Dev schedules
- `settings.yml` - Dev AAP settings (permissive, verbose logging)

**`group_vars/aap_qa/`** - QA environment:
- Similar structure to dev, but with version-locked images and stricter settings
- Projects don't auto-update
- Additional validation job templates

**`group_vars/aap_prod/`** - Production environment:
- Fully version-locked (all versions from release manifest)
- Most restrictive settings
- Additional workflow templates for deployment orchestration
- Notification templates for alerts

## How It Works

### 1. Developer Workflow

```bash
# 1. Clone repository
git clone https://github.com/djdanielsson/rh1-aap-config-as-code.git
cd aap-config-as-code

# 2. Create feature branch
git checkout -b feature/new-job-template

# 3. Edit configuration (e.g., add new job template)
vi group_vars/aap_dev/job_templates.yml

# 4. Commit and push
git add group_vars/aap_dev/job_templates.yml
git commit -m "Add new job template for network automation"
git push origin feature/new-job-template

# 5. Create Pull Request
gh pr create --title "Add network automation job template"

# 6. After PR approved and merged to main:
#    - GitHub webhook triggers CaC pipeline
#    - Tekton applies changes to Dev AAP automatically
#    - Review in Dev AAP UI
```

### 2. Automatic Pipeline Trigger

When you push to `main` branch:
1. GitHub webhook fires to OpenShift Tekton EventListener
2. CaC Pipeline triggered with commit SHA
3. Pipeline clones this repo at the commit
4. Runs `ansible-playbook playbook.yml --limit aap_dev`
5. `infra.aap_configuration` collection applies changes to Dev AAP via API
6. Configuration is now live in Dev AAP

### 3. Promotion to QA/Prod

Configuration is promoted via **Release Manifest** (not direct push):

```bash
# In automation-release-manifest repository
cat releases/release-26.01.06.0.yml
---
version: "26.01.06.0"
components:
  aap_configuration: "abc123..."  # This commit SHA from aap-config-as-code
  execution_environment: "def456..."
  collections: "ghi789..."
```

When you tag a release, the Promotion Pipeline:
1. Parses the manifest
2. Clones aap-config-as-code at the specified commit SHA
3. Applies to QA or Prod AAP
4. Result: Atomic, version-locked deployment

## Configuration Guidelines

### 1. No Secrets in Git (Constitution Article V)

❌ **NEVER** put actual secrets in this repository:
```yaml
# BAD - Do not do this!
controller_credentials:
  - name: AWS Access Key
    credential_type: Amazon Web Services
    inputs:
      username: AKIAIOSFODNN7EXAMPLE  # NEVER!
      password: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  # NEVER!
```

✅ **DO** reference OCP secrets:
```yaml
# GOOD - Reference external secrets
controller_credentials:
  - name: AWS Access Key
    credential_type: Amazon Web Services
    organization: Default
    inputs:
      username: "{{ lookup('env', 'AWS_ACCESS_KEY_ID') }}"
      password: "{{ lookup('env', 'AWS_SECRET_ACCESS_KEY') }}"
```

The Tekton pipeline mounts secrets as environment variables before running the playbook.

### 2. Idempotency (Constitution Article IV)

All configuration must be idempotent - safe to run multiple times:

✅ Configuration is declarative (describe desired state)  
✅ `infra.aap_configuration` collection handles idempotency  
✅ Re-running playbook with same config = no changes

### 3. Environment-Specific Configuration

Use group_vars to separate environments:

```yaml
# group_vars/aap_dev.yml
controller_execution_environments:
  - name: "Web EE"
    image: "quay.io/ansible/awx-ee:latest"  # Latest for dev

# group_vars/aap_prod.yml
controller_execution_environments:
  - name: "Web EE"
    image: "registry.example.com/web-ee:26.01.06.0"  # Pinned version for prod
```

### 4. Organization Structure

Recommended AAP organization layout:

```yaml
controller_organizations:
  - name: Platform
    description: Platform automation (infrastructure, networking)
  
  - name: Applications
    description: Application deployment and configuration
  
  - name: Security
    description: Security scanning and compliance
```

## Testing

### Local Testing

You can test configuration changes locally before pushing:

```bash
# 1. Install collections
ansible-galaxy collection install -r collections/requirements.yml

# 2. Set AAP connection details (from HashiCorp Vault or local env)
export CONTROLLER_HOST="https://aap-dev-aap-dev.apps.cluster.example.com"
export CONTROLLER_OAUTH_TOKEN="your-dev-token-here"

# 3. Run playbook against dev (dry-run)
ansible-playbook playbooks/playbook.yml --limit aap_dev --check

# 4. Apply to dev (if checks pass)
ansible-playbook playbooks/playbook.yml --limit aap_dev
```

**Note**: You need an AAP API token. Get it from HashiCorp Vault or the AAP UI.

### CI/CD Testing (Ephemeral AAP)

On every commit/PR, the CI pipeline validates configuration by:

1. **Spinning up a temporary AAP instance** in an ephemeral namespace
2. **Applying the full CaC configuration** to the temp AAP
3. **Running validation tests** to ensure config applied correctly
4. **Tearing down the temp AAP** regardless of pass/fail

This ensures configuration is valid before merging without affecting real environments.

```yaml
# Pipeline flow:
# 1. Create temp namespace (aap-cac-test-<sha>)
# 2. Deploy AAP operator + CR
# 3. Wait for AAP ready
# 4. Run: ansible-playbook playbooks/playbook.yml --limit aap_test
# 5. Validate: Check AAP API for expected resources
# 6. Cleanup: Delete namespace
# 7. Report: Pass/Fail status on PR
```

### Secrets for Testing

Testing uses HashiCorp Vault for secrets:

```yaml
# Vault paths for test secrets
secret/data/aap-cac-test:
  controller_host: "<auto-generated-route>"
  controller_password: "<auto-generated>"
```

## Common Operations

### Add New Job Template

Edit `group_vars/aap_dev/job_templates.yml` and use wildcards for organization:

```yaml
# Add to existing controller_job_templates_dev_web list
controller_job_templates_dev_web:
  - name: "Deploy Web Application"
    description: "Deploys web app to target servers"
    job_type: run
    organization: Applications
    inventory: Dev Servers
    project: Platform Automation
    playbook: deploy_web_app.yml
    execution_environment: Web EE (Dev)
    credentials:
      - Dev SSH Key
    ask_variables_on_launch: true
```

Or create a new wildcard group in the same file:

```yaml
# New section for database templates
controller_job_templates_dev_database:
  - name: "Backup Database"
    description: "Backs up database to S3"
    job_type: run
    organization: Applications
    inventory: Dev Servers
    project: Platform Automation
    playbook: backup_db.yml
    execution_environment: Default Execution Environment
```

### Add New Project (SCM Connection)

Edit `group_vars/aap_dev/projects.yml`:

```yaml
# Add to existing controller_projects_dev_platform or create new wildcard
controller_projects_dev_networking:
  - name: "Network Automation"
    organization: Platform
    scm_type: git
    scm_url: https://github.com/org/network-automation.git
    scm_branch: develop  # develop for dev environment
    scm_update_on_launch: true
    credential: Dev GitHub Token
    default_environment: Default Execution Environment
```

### Add Custom Credential Type

The repository includes an example in `group_vars/all/credential_types.yml` following the [official aap_configuration_template pattern](https://github.com/redhat-cop/aap_configuration_template):

```yaml
controller_credential_types_all:
  - name: HashiCorp Vault Secret Lookup
    description: Credentials for HashiCorp Vault secret lookups
    kind: cloud
    inputs:
      fields:
        - id: vault_url
          type: string
          label: Vault Server URL
        - id: vault_token
          type: string
          label: Vault Token
          secret: true
      required:
        - vault_url
        - vault_token
    injectors:
      env:
        VAULT_ADDR: !unsafe "{{ vault_url }}"
        VAULT_TOKEN: !unsafe "{{ vault_token }}"
      extra_vars:
        vault_addr: !unsafe "{{ vault_url }}"
        vault_token: !unsafe "{{ vault_token }}"
```

**Note**: Use `!unsafe` tag for Jinja2 templates to prevent double interpolation.

Then reference it in your credentials (e.g., `group_vars/aap_prod/credentials.yml`):

```yaml
controller_credentials_prod_vault:
  - name: Production Vault
    organization: Default
    credential_type: HashiCorp Vault Secret Lookup
    inputs:
      url: "{{ lookup('env', 'VAULT_ADDR') }}"
      token: "{{ lookup('env', 'VAULT_TOKEN') }}"
```

## Troubleshooting

### Pipeline Fails with "Authentication Error"

Check AAP API credentials:
```bash
oc get secret aap-dev-api-credentials -n dev-tools -o yaml
```

### Configuration Not Applied

1. Check pipeline logs:
   ```bash
   tkn pipelinerun logs -f -n dev-tools <run-name>
   ```

2. Verify AAP connectivity:
   ```bash
   curl -k https://aap-dev-route/api/v2/ping/
   ```

3. Check for YAML syntax errors:
   ```bash
   ansible-playbook playbook.yml --syntax-check
   ```

### Idempotency Issues

If playbook reports changes on every run, check:
- Are you using unique names/identifiers?
- Are there dynamic values (timestamps, random strings)?
- Review `infra.aap_configuration` collection documentation

## Links

### Related Repositories
- **Cluster Config** (Platform GitOps): https://github.com/djdanielsson/rh1-cluster-config
- **Ansible Collection**: https://github.com/djdanielsson/rh1-custom-collection
- **Execution Environment**: https://github.com/djdanielsson/rh1-custom-ee
- **Release Manifests**: https://github.com/djdanielsson/rh1-release-manifest

### Documentation
- **Project Workspace**: https://github.com/djdanielsson/rh1_ansible_code_lifecycle
- **Quickstart Guide**: https://github.com/djdanielsson/rh1_ansible_code_lifecycle/blob/main/docs/GETTING-STARTED.md
- **Constitution**: https://github.com/djdanielsson/rh1_ansible_code_lifecycle/blob/main/.specify/memory/constitution.md

### External Resources
- **Collection Docs**: https://github.com/redhat-cop/aap_configuration
- **AAP API Docs**: https://docs.ansible.com/automation-controller/latest/html/controllerapi/

- **Constitution**: See `.specify/memory/constitution.md` in cluster-config repo

---

**Last Updated**: 2025-10-29  
**Maintained By**: Platform Team  
**Questions**: File issue in cluster-config repository

