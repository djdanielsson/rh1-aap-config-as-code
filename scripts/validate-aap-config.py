#!/usr/bin/env python3
"""
Validate AAP Configuration as Code files.

This script validates Ansible Automation Platform configuration files
to ensure constitutional compliance, best practices, and data integrity.

Constitutional Alignment:
- Article II: Separation of Duties - Validates RBAC configuration
- Article IV: Production-Grade Quality - Ensures quality standards
- Article V: Zero-Trust Security - Validates credential references

Usage:
    ./validate-aap-config.py
    ./validate-aap-config.py --environment dev
    ./validate-aap-config.py --check-credentials
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

try:
    import yaml
except ImportError:
    print("❌ Error: PyYAML package not installed")
    print("Install with: pip install PyYAML")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class AAPConfigValidator:
    """Validates AAP Configuration as Code."""
    
    def __init__(self, base_path: Path, environment: str = None):
        self.base_path = base_path
        self.environment = environment
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
        # Tracking references
        self.defined_credentials: Set[str] = set()
        self.defined_projects: Set[str] = set()
        self.defined_inventories: Set[str] = set()
        self.defined_ees: Set[str] = set()
        self.defined_organizations: Set[str] = set()
        self.defined_teams: Set[str] = set()
        
        self.referenced_credentials: Set[str] = set()
        self.referenced_projects: Set[str] = set()
        self.referenced_inventories: Set[str] = set()
        self.referenced_ees: Set[str] = set()
    
    def load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse YAML file."""
        try:
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                return content if content else {}
        except FileNotFoundError:
            self.warnings.append(f"File not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error in {file_path}: {e}")
            return {}
    
    def get_group_vars_path(self, environment: str = None) -> Path:
        """Get path to group_vars for specified environment."""
        if environment:
            return self.base_path / 'inventory' / 'group_vars' / f'aap_{environment}'
        return self.base_path / 'inventory' / 'group_vars'
    
    def validate_organizations(self, config: Dict[str, Any]) -> None:
        """Validate organization configuration."""
        orgs = config.get('controller_organizations', [])
        
        if not orgs:
            self.warnings.append("No organizations defined")
            return
        
        for org in orgs:
            name = org.get('name', 'unnamed')
            self.defined_organizations.add(name)
            
            # Check required fields
            if 'name' not in org:
                self.errors.append("Organization missing 'name' field")
            
            # Check for description
            if 'description' not in org:
                self.warnings.append(
                    f"Organization '{name}' missing description"
                )
        
        self.info.append(f"Found {len(orgs)} organization(s)")
    
    def validate_teams(self, config: Dict[str, Any]) -> None:
        """Validate team configuration (Article II: Separation of Duties)."""
        teams = config.get('controller_teams', [])
        
        if not teams:
            self.warnings.append("No teams defined - consider RBAC best practices")
            return
        
        for team in teams:
            name = team.get('name', 'unnamed')
            self.defined_teams.add(name)
            
            # Check required fields
            if 'name' not in team:
                self.errors.append("Team missing 'name' field")
            
            if 'organization' not in team:
                self.errors.append(f"Team '{name}' missing organization reference")
            
            # Check for description
            if 'description' not in team:
                self.warnings.append(f"Team '{name}' missing description")
        
        self.info.append(f"Found {len(teams)} team(s)")
    
    def validate_credentials(self, config: Dict[str, Any]) -> None:
        """Validate credential configuration (Article V: Zero-Trust Security)."""
        credentials = config.get('controller_credentials', [])
        
        for cred in credentials:
            name = cred.get('name', 'unnamed')
            self.defined_credentials.add(name)
            
            # Check required fields
            if 'name' not in cred:
                self.errors.append("Credential missing 'name' field")
            
            if 'credential_type' not in cred:
                self.errors.append(f"Credential '{name}' missing credential_type")
            
            if 'organization' not in cred:
                self.errors.append(f"Credential '{name}' missing organization")
            
            # Security validations
            inputs = cred.get('inputs', {})
            
            # Check for hardcoded secrets (should use vault)
            sensitive_fields = ['password', 'secret', 'token', 'private_key']
            for field in sensitive_fields:
                if field in inputs:
                    value = str(inputs[field])
                    # Check if it's a vault reference
                    if not value.startswith('{{ ') and not value.startswith('!vault'):
                        self.errors.append(
                            f"Credential '{name}' has unencrypted '{field}' - "
                            f"use ansible-vault or lookup"
                        )
        
        self.info.append(f"Found {len(credentials)} credential(s)")
    
    def validate_execution_environments(self, config: Dict[str, Any]) -> None:
        """Validate execution environment configuration."""
        ees = config.get('controller_execution_environments', [])
        
        for ee in ees:
            name = ee.get('name', 'unnamed')
            self.defined_ees.add(name)
            
            # Check required fields
            if 'name' not in ee:
                self.errors.append("Execution Environment missing 'name' field")
            
            if 'image' not in ee:
                self.errors.append(f"Execution Environment '{name}' missing image")
            else:
                image = ee['image']
                # Check for digest-based image reference (immutability)
                if '@sha256:' not in image and self.environment == 'prod':
                    self.warnings.append(
                        f"Execution Environment '{name}' should use digest-based "
                        f"image reference in production"
                    )
                
                # Check for 'latest' tag
                if ':latest' in image:
                    self.errors.append(
                        f"Execution Environment '{name}' uses 'latest' tag - "
                        f"use specific version"
                    )
        
        self.info.append(f"Found {len(ees)} execution environment(s)")
    
    def validate_projects(self, config: Dict[str, Any]) -> None:
        """Validate project configuration (Article I: GitOps First)."""
        projects = config.get('controller_projects', [])
        
        for project in projects:
            name = project.get('name', 'unnamed')
            self.defined_projects.add(name)
            
            # Check required fields
            if 'name' not in project:
                self.errors.append("Project missing 'name' field")
            
            if 'scm_type' not in project:
                self.errors.append(f"Project '{name}' missing scm_type")
            elif project['scm_type'] != 'git':
                self.warnings.append(
                    f"Project '{name}' not using Git SCM "
                    f"(Constitutional Article I: GitOps First)"
                )
            
            if 'scm_url' not in project:
                self.errors.append(f"Project '{name}' missing scm_url")
            
            # Check for branch specification
            if 'scm_branch' not in project:
                self.warnings.append(
                    f"Project '{name}' not specifying branch - "
                    f"will use repository default"
                )
            
            # Check for credential
            if 'credential' in project:
                self.referenced_credentials.add(project['credential'])
            
            # Check for execution environment
            if 'default_environment' in project:
                self.referenced_ees.add(project['default_environment'])
        
        self.info.append(f"Found {len(projects)} project(s)")
    
    def validate_inventories(self, config: Dict[str, Any]) -> None:
        """Validate inventory configuration."""
        inventories = config.get('controller_inventories', [])
        
        for inventory in inventories:
            name = inventory.get('name', 'unnamed')
            self.defined_inventories.add(name)
            
            # Check required fields
            if 'name' not in inventory:
                self.errors.append("Inventory missing 'name' field")
            
            if 'organization' not in inventory:
                self.errors.append(f"Inventory '{name}' missing organization")
        
        self.info.append(f"Found {len(inventories)} inventor(y|ies)")
    
    def validate_job_templates(self, config: Dict[str, Any]) -> None:
        """Validate job template configuration."""
        templates = config.get('controller_templates', [])
        
        for template in templates:
            name = template.get('name', 'unnamed')
            
            # Check required fields
            if 'name' not in template:
                self.errors.append("Job Template missing 'name' field")
            
            # Check for project reference
            if 'project' in template:
                self.referenced_projects.add(template['project'])
            else:
                self.errors.append(f"Job Template '{name}' missing project")
            
            # Check for inventory reference
            if 'inventory' in template:
                self.referenced_inventories.add(template['inventory'])
            else:
                self.errors.append(f"Job Template '{name}' missing inventory")
            
            # Check for playbook
            if 'playbook' not in template:
                self.errors.append(f"Job Template '{name}' missing playbook")
            
            # Check for credentials
            if 'credentials' in template:
                for cred in template['credentials']:
                    if isinstance(cred, str):
                        self.referenced_credentials.add(cred)
                    elif isinstance(cred, dict) and 'name' in cred:
                        self.referenced_credentials.add(cred['name'])
            
            # Check for execution environment
            if 'execution_environment' in template:
                self.referenced_ees.add(template['execution_environment'])
            
            # Production-specific checks (Article IV: Production-Grade Quality)
            if self.environment == 'prod':
                if template.get('ask_variables_on_launch', False):
                    self.warnings.append(
                        f"Job Template '{name}' allows variable prompts in "
                        f"production - consider pre-defining variables"
                    )
                
                if not template.get('use_fact_cache', False):
                    self.warnings.append(
                        f"Job Template '{name}' not using fact cache - "
                        f"consider enabling for performance"
                    )
        
        self.info.append(f"Found {len(templates)} job template(s)")
    
    def validate_workflow_templates(self, config: Dict[str, Any]) -> None:
        """Validate workflow template configuration."""
        workflows = config.get('controller_workflows', [])
        
        for workflow in workflows:
            name = workflow.get('name', 'unnamed')
            
            # Check required fields
            if 'name' not in workflow:
                self.errors.append("Workflow Template missing 'name' field")
            
            # Check for workflow nodes
            if 'simplified_workflow_nodes' not in workflow and 'workflow_nodes' not in workflow:
                self.warnings.append(
                    f"Workflow Template '{name}' has no workflow nodes defined"
                )
        
        self.info.append(f"Found {len(workflows)} workflow template(s)")
    
    def validate_schedules(self, config: Dict[str, Any]) -> None:
        """Validate schedule configuration."""
        schedules = config.get('controller_schedules', [])
        
        for schedule in schedules:
            name = schedule.get('name', 'unnamed')
            
            # Check required fields
            if 'name' not in schedule:
                self.errors.append("Schedule missing 'name' field")
            
            if 'rrule' not in schedule:
                self.errors.append(f"Schedule '{name}' missing rrule")
            
            if 'unified_job_template' not in schedule:
                self.errors.append(
                    f"Schedule '{name}' missing unified_job_template"
                )
            
            # Check if enabled
            if schedule.get('enabled', True) and self.environment == 'prod':
                self.info.append(
                    f"Schedule '{name}' is enabled in production"
                )
        
        self.info.append(f"Found {len(schedules)} schedule(s)")
    
    def validate_references(self) -> None:
        """Validate that all references point to defined resources."""
        # Check credential references
        undefined_creds = self.referenced_credentials - self.defined_credentials
        if undefined_creds:
            for cred in undefined_creds:
                self.warnings.append(
                    f"Referenced credential '{cred}' is not defined "
                    f"(may be in different environment)"
                )
        
        # Check project references
        undefined_projects = self.referenced_projects - self.defined_projects
        if undefined_projects:
            for project in undefined_projects:
                self.warnings.append(
                    f"Referenced project '{project}' is not defined "
                    f"(may be in different environment)"
                )
        
        # Check inventory references
        undefined_inventories = self.referenced_inventories - self.defined_inventories
        if undefined_inventories:
            for inventory in undefined_inventories:
                self.warnings.append(
                    f"Referenced inventory '{inventory}' is not defined "
                    f"(may be in different environment)"
                )
        
        # Check EE references
        undefined_ees = self.referenced_ees - self.defined_ees
        if undefined_ees:
            for ee in undefined_ees:
                self.warnings.append(
                    f"Referenced execution environment '{ee}' is not defined "
                    f"(may be in different environment)"
                )
    
    def validate_environment(self, environment: str) -> bool:
        """Validate all configuration files for a specific environment."""
        print(f"\n{Colors.BLUE}{Colors.BOLD}🔍 Validating AAP Configuration{Colors.RESET}")
        print(f"Environment: {environment}")
        print()
        
        group_vars_path = self.get_group_vars_path(environment)
        
        if not group_vars_path.exists():
            self.errors.append(f"Environment path not found: {group_vars_path}")
            return False
        
        # Define validation mapping
        config_files = {
            'organizations.yml': self.validate_organizations,
            'teams.yml': self.validate_teams,
            'credentials.yml': self.validate_credentials,
            'execution_environments.yml': self.validate_execution_environments,
            'projects.yml': self.validate_projects,
            'inventories.yml': self.validate_inventories,
            'job_templates.yml': self.validate_job_templates,
            'workflow_templates.yml': self.validate_workflow_templates,
            'schedules.yml': self.validate_schedules,
        }
        
        # Validate each configuration file
        for filename, validator in config_files.items():
            file_path = group_vars_path / filename
            if file_path.exists():
                print(f"Validating {filename}...")
                config = self.load_yaml_file(file_path)
                if config:
                    validator(config)
        
        # Validate references
        print("Validating cross-references...")
        self.validate_references()
        
        return True
    
    def print_results(self) -> bool:
        """Print validation results and return success status."""
        print(f"\n{Colors.BLUE}{Colors.BOLD}📊 Validation Results{Colors.RESET}\n")
        
        # Print errors
        if self.errors:
            print(f"{Colors.RED}{Colors.BOLD}❌ Errors ({len(self.errors)}):{Colors.RESET}")
            for error in self.errors:
                print(f"   {error}")
            print()
        
        # Print warnings
        if self.warnings:
            print(f"{Colors.YELLOW}⚠️  Warnings ({len(self.warnings)}):{Colors.RESET}")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
        
        # Print info
        if self.info:
            print(f"{Colors.BLUE}ℹ️  Information:{Colors.RESET}")
            for info in self.info:
                print(f"   {info}")
            print()
        
        # Summary
        if self.errors:
            print(f"{Colors.RED}{Colors.BOLD}❌ Validation failed with {len(self.errors)} error(s){Colors.RESET}")
            return False
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ Validation passed!{Colors.RESET}")
            if self.warnings:
                print(f"{Colors.YELLOW}Note: {len(self.warnings)} warning(s) found{Colors.RESET}")
            return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate AAP Configuration as Code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --environment dev
  %(prog)s --environment prod
  %(prog)s --environment qa
  %(prog)s --all-environments
        """
    )
    parser.add_argument(
        '--environment', '-e',
        choices=['dev', 'qa', 'prod', 'all'],
        default='dev',
        help='Environment to validate (default: dev)'
    )
    parser.add_argument(
        '--all-environments',
        action='store_true',
        help='Validate all environments'
    )
    parser.add_argument(
        '--base-path',
        type=Path,
        default=Path.cwd(),
        help='Base path to aap-config-as-code repository'
    )
    
    args = parser.parse_args()
    
    # Determine which environments to validate
    if args.all_environments or args.environment == 'all':
        environments = ['dev', 'qa', 'prod']
    else:
        environments = [args.environment]
    
    # Validate each environment
    all_passed = True
    for env in environments:
        validator = AAPConfigValidator(args.base_path, env)
        validator.validate_environment(env)
        passed = validator.print_results()
        all_passed = all_passed and passed
        
        if len(environments) > 1:
            print("\n" + "="*80 + "\n")
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()

