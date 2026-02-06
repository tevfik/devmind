"""
Configuration Validation for Yaver AI
Validates configuration and provides helpful error messages
"""

from typing import Dict, List, Optional
from pathlib import Path
import requests

from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """Validates Yaver configuration"""

    def __init__(self, config):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        self.validate_ollama()
        self.validate_vector_db()
        self.validate_neo4j()
        self.validate_paths()

        if self.errors:
            logger.error(
                f"Configuration validation failed with {len(self.errors)} errors"
            )
            for error in self.errors:
                logger.error(f"  - {error}")
            return False

        if self.warnings:
            logger.warning(f"Configuration has {len(self.warnings)} warnings")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        logger.info("Configuration validation passed")
        return True

    def validate_ollama(self):
        """Validate Ollama configuration"""
        try:
            url = self.config.ollama.base_url
            response = requests.get(url, timeout=2)
            if response.status_code != 200:
                self.warnings.append(
                    f"Ollama at {url} returned status {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            self.warnings.append(
                f"Cannot connect to Ollama at {self.config.ollama.base_url}. "
                "Make sure Ollama is running."
            )
        except Exception as e:
            self.warnings.append(f"Error checking Ollama: {e}")

    def validate_vector_db(self):
        """Validate vector database configuration"""
        provider = self.config.vector_db.provider

        if provider not in ["qdrant", "chroma"]:
            self.errors.append(
                f"Invalid vector DB provider: {provider}. Must be 'qdrant' or 'chroma'"
            )
            return

        if provider == "qdrant":
            try:
                url = f"http://{self.config.qdrant.host}:{self.config.qdrant.port}"
                response = requests.get(url, timeout=2)
                if response.status_code != 200:
                    self.warnings.append(
                        f"Qdrant at {url} returned status {response.status_code}"
                    )
            except requests.exceptions.ConnectionError:
                self.warnings.append(
                    f"Cannot connect to Qdrant at {url}. Make sure Qdrant is running."
                )
            except Exception as e:
                self.warnings.append(f"Error checking Qdrant: {e}")

        elif provider == "chroma":
            persist_dir = Path(self.config.vector_db.chroma_persist_dir)
            if not persist_dir.exists():
                logger.info(
                    f"ChromaDB persist directory will be created: {persist_dir}"
                )

    def validate_neo4j(self):
        """Validate Neo4j configuration"""
        try:
            from neo4j import GraphDatabase

            uri = self.config.neo4j.uri
            user = self.config.neo4j.user
            password = self.config.neo4j.password

            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            driver.close()
            logger.debug("Neo4j connection verified")
        except ImportError:
            self.warnings.append(
                "neo4j package not installed. Install with: pip install neo4j"
            )
        except Exception as e:
            self.warnings.append(
                f"Cannot connect to Neo4j at {self.config.neo4j.uri}: {e}"
            )

    def validate_paths(self):
        """Validate file paths in configuration"""
        # Check output directory
        output_dir = Path(self.config.project.default_output_dir)
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created output directory: {output_dir}")
            except Exception as e:
                self.errors.append(f"Cannot create output directory {output_dir}: {e}")

        # Check backup directory if enabled
        if self.config.project.enable_backup:
            backup_dir = Path(self.config.project.backup_dir).expanduser()
            if not backup_dir.exists():
                try:
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created backup directory: {backup_dir}")
                except Exception as e:
                    self.warnings.append(
                        f"Cannot create backup directory {backup_dir}: {e}"
                    )

    def get_summary(self) -> Dict[str, List[str]]:
        """Get validation summary"""
        return {"errors": self.errors, "warnings": self.warnings}


def validate_config(config) -> bool:
    """
    Validate configuration and return True if valid

    Args:
        config: YaverConfig instance

    Returns:
        True if configuration is valid, False otherwise
    """
    validator = ConfigValidator(config)
    return validator.validate_all()
