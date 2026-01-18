"""
ADLS Persistence for Chat History.

Uses Azure Data Lake Storage Gen2 for long-term chat history storage.
Authentication via DefaultAzureCredential (no API keys).
Supports client-side encryption using Azure Key Vault.
"""

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


# Encryption constants
ENCRYPTION_VERSION = 1
AES_KEY_SIZE = 32  # 256 bits
AES_NONCE_SIZE = 12  # 96 bits for GCM
AES_TAG_SIZE = 16  # 128 bits


@dataclass
class EncryptionConfig:
    """Client-side encryption configuration."""
    enabled: bool = False
    # Key Vault URL for key encryption key (KEK)
    key_vault_url: str = ""
    # Key name in Key Vault
    key_name: str = "chat-history-kek"
    # Key version (empty = latest)
    key_version: str = ""
    # Algorithm for key wrapping
    algorithm: str = "RSA-OAEP-256"


@dataclass
class PersistenceConfig:
    """ADLS persistence configuration."""
    enabled: bool = False
    account_name: str = ""
    container: str = "chat-history"
    folder: str = "threads"
    # Schedule: persist X seconds before cache TTL expires
    # Format: "ttl+300" means persist 300s before TTL (5 min buffer)
    schedule: str = "ttl+300"
    # Encryption settings
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)


class ClientSideEncryption:
    """
    Client-side encryption for ADLS persistence using Azure Key Vault.

    Uses envelope encryption:
    1. Generate a random AES-256-GCM data encryption key (DEK) per blob
    2. Encrypt data with DEK
    3. Wrap DEK with Key Vault key encryption key (KEK)
    4. Store wrapped DEK + encrypted data together
    """

    def __init__(self, config: EncryptionConfig):
        """Initialize encryption with Key Vault configuration."""
        self.config = config
        self._crypto_client = None
        self._initialized = False

    async def _ensure_initialized(self) -> bool:
        """Initialize Key Vault crypto client."""
        if not self.config.enabled:
            return False

        if self._initialized:
            return self._crypto_client is not None

        self._initialized = True

        if not self.config.key_vault_url or not self.config.key_name:
            logger.warning("Encryption enabled but Key Vault not configured")
            return False

        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.keyvault.keys.crypto.aio import CryptographyClient
            from azure.keyvault.keys.aio import KeyClient

            credential = DefaultAzureCredential()

            # Get the key from Key Vault
            key_client = KeyClient(
                vault_url=self.config.key_vault_url,
                credential=credential
            )

            if self.config.key_version:
                key = await key_client.get_key(
                    self.config.key_name,
                    self.config.key_version
                )
            else:
                key = await key_client.get_key(self.config.key_name)

            await key_client.close()

            # Create crypto client for wrap/unwrap operations
            self._crypto_client = CryptographyClient(key, credential)

            logger.info(
                "Client-side encryption initialized",
                key_vault=self.config.key_vault_url,
                key_name=self.config.key_name
            )
            return True

        except ImportError:
            logger.warning(
                "azure-keyvault-keys not installed, encryption disabled"
            )
            return False
        except Exception as e:
            logger.error("Failed to initialize encryption", error=str(e))
            return False

    async def encrypt(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Encrypt data using envelope encryption.

        Args:
            data: Plain data bytes

        Returns:
            Dict with encrypted_data, wrapped_key, nonce, tag, and version
        """
        if not await self._ensure_initialized():
            return None

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from azure.keyvault.keys.crypto import KeyWrapAlgorithm

            # Generate random DEK and nonce
            dek = secrets.token_bytes(AES_KEY_SIZE)
            nonce = secrets.token_bytes(AES_NONCE_SIZE)

            # Encrypt data with AES-256-GCM
            aesgcm = AESGCM(dek)
            ciphertext = aesgcm.encrypt(nonce, data, None)

            # Wrap DEK with Key Vault KEK
            algorithm = getattr(
                KeyWrapAlgorithm,
                self.config.algorithm.replace("-", "_"),
                KeyWrapAlgorithm.rsa_oaep_256
            )
            wrap_result = await self._crypto_client.wrap_key(algorithm, dek)

            return {
                "version": ENCRYPTION_VERSION,
                "algorithm": "AES-256-GCM",
                "key_wrap_algorithm": self.config.algorithm,
                "wrapped_key": base64.b64encode(wrap_result.encrypted_key).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "encrypted_data": base64.b64encode(ciphertext).decode(),
                "key_id": wrap_result.key_id
            }

        except ImportError:
            logger.error("cryptography package not installed")
            return None
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            return None

    async def decrypt(self, envelope: Dict[str, Any]) -> Optional[bytes]:
        """
        Decrypt envelope-encrypted data.

        Args:
            envelope: Dict from encrypt() method

        Returns:
            Decrypted data bytes
        """
        if not await self._ensure_initialized():
            return None

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from azure.keyvault.keys.crypto import KeyWrapAlgorithm

            # Validate version
            version = envelope.get("version", 0)
            if version != ENCRYPTION_VERSION:
                logger.error("Unknown encryption version", version=version)
                return None

            # Decode components
            wrapped_key = base64.b64decode(envelope["wrapped_key"])
            nonce = base64.b64decode(envelope["nonce"])
            ciphertext = base64.b64decode(envelope["encrypted_data"])

            # Unwrap DEK with Key Vault KEK
            algorithm = getattr(
                KeyWrapAlgorithm,
                envelope.get("key_wrap_algorithm", "RSA-OAEP-256").replace("-", "_"),
                KeyWrapAlgorithm.rsa_oaep_256
            )
            unwrap_result = await self._crypto_client.unwrap_key(algorithm, wrapped_key)
            dek = unwrap_result.key

            # Decrypt data with AES-256-GCM
            aesgcm = AESGCM(dek)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext

        except ImportError:
            logger.error("cryptography package not installed")
            return None
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            return None

    async def close(self) -> None:
        """Close the crypto client."""
        if self._crypto_client:
            await self._crypto_client.close()
            self._crypto_client = None


class ADLSPersistence:
    """
    Azure Data Lake Storage Gen2 for chat history persistence.

    Uses DefaultAzureCredential - no API keys required.
    Stores serialized chat threads as JSON blobs.
    Supports client-side encryption using Azure Key Vault.
    """

    def __init__(self, config: PersistenceConfig):
        """
        Initialize ADLS persistence.

        Args:
            config: PersistenceConfig with storage settings
        """
        self.config = config
        self._client = None
        self._container_client = None
        self._initialized = False

        # Initialize encryption if enabled
        self._encryption: Optional[ClientSideEncryption] = None
        if config.encryption.enabled:
            self._encryption = ClientSideEncryption(config.encryption)
            logger.info("Client-side encryption enabled for ADLS persistence")

        if not config.enabled:
            logger.info("ADLS persistence disabled")
            return

        if not config.account_name:
            logger.warning("ADLS persistence enabled but no account configured")
            self.config.enabled = False
    
    async def _ensure_connected(self) -> bool:
        """Ensure ADLS connection is established."""
        if not self.config.enabled:
            return False
            
        if self._initialized:
            return self._container_client is not None
        
        self._initialized = True
        
        try:
            # Try blob storage API first (works with any storage account)
            # ADLS Gen2 DFS API requires hierarchical namespace which may not be enabled
            from azure.storage.blob.aio import BlobServiceClient
            from azure.identity.aio import DefaultAzureCredential
            
            credential = DefaultAzureCredential()
            
            # Use blob endpoint instead of DFS
            account_url = f"https://{self.config.account_name}.blob.core.windows.net"
            self._client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
            
            self._container_client = self._client.get_container_client(
                self.config.container
            )
            
            # Check if container exists
            try:
                await self._container_client.get_container_properties()
            except Exception:
                logger.info("Creating container", container=self.config.container)
                await self._container_client.create_container()
            
            # Store flag for API type
            self._using_blob_api = True
            
            logger.info(
                "ADLS persistence connected",
                account=self.config.account_name,
                container=self.config.container
            )
            return True
            
        except ImportError:
            logger.warning("azure-storage-blob not installed, persistence disabled")
            self.config.enabled = False
            return False
        except Exception as e:
            logger.warning("ADLS connection failed", error=str(e))
            self._container_client = None
            return False
    
    def _make_path(self, chat_id: str) -> str:
        """Create blob path for chat ID."""
        return f"{self.config.folder}/{chat_id}.json"
    
    async def get(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Load serialized thread from ADLS.

        Args:
            chat_id: The chat session ID

        Returns:
            Serialized thread data or None if not found
        """
        if not await self._ensure_connected():
            return None

        try:
            path = self._make_path(chat_id)
            blob_client = self._container_client.get_blob_client(path)

            download = await blob_client.download_blob()
            content = await download.readall()
            data = json.loads(content.decode('utf-8'))

            # Check if data is encrypted
            if data.get("_encrypted") and self._encryption:
                envelope = data.get("_encryption_envelope")
                if envelope:
                    decrypted_bytes = await self._encryption.decrypt(envelope)
                    if decrypted_bytes:
                        data = json.loads(decrypted_bytes.decode('utf-8'))
                    else:
                        logger.error("Failed to decrypt data", chat_id=chat_id)
                        return None
                else:
                    logger.error("Encrypted data missing envelope", chat_id=chat_id)
                    return None
            elif data.get("_encrypted") and not self._encryption:
                logger.error(
                    "Data is encrypted but encryption not configured",
                    chat_id=chat_id
                )
                return None

            logger.debug("ADLS load success", chat_id=chat_id)
            return data

        except Exception as e:
            # File not found is expected for new chats
            if "BlobNotFound" in str(e) or "PathNotFound" in str(e):
                logger.debug("ADLS file not found", chat_id=chat_id)
            else:
                logger.warning("ADLS load failed", chat_id=chat_id, error=str(e))
            return None
    
    async def save(
        self,
        chat_id: str,
        thread_data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Save serialized thread to ADLS.

        Args:
            chat_id: The chat session ID
            thread_data: Serialized thread data
            metadata: Optional metadata to attach to blob

        Returns:
            True if saved successfully
        """
        if not await self._ensure_connected():
            return False

        try:
            path = self._make_path(chat_id)
            blob_client = self._container_client.get_blob_client(path)

            # Add timestamp to data
            thread_data["_persisted_at"] = datetime.now(timezone.utc).isoformat()
            thread_data["_chat_id"] = chat_id

            # Encrypt if encryption is enabled
            if self._encryption and self.config.encryption.enabled:
                plain_bytes = json.dumps(thread_data, default=str).encode('utf-8')
                envelope = await self._encryption.encrypt(plain_bytes)

                if envelope:
                    # Store encrypted envelope with metadata wrapper
                    encrypted_wrapper = {
                        "_encrypted": True,
                        "_encryption_envelope": envelope,
                        "_chat_id": chat_id,
                        "_persisted_at": thread_data["_persisted_at"]
                    }
                    content = json.dumps(encrypted_wrapper, indent=2)
                    logger.debug("Saving encrypted data", chat_id=chat_id)
                else:
                    logger.warning(
                        "Encryption failed, saving unencrypted",
                        chat_id=chat_id
                    )
                    content = json.dumps(thread_data, indent=2, default=str)
            else:
                content = json.dumps(thread_data, indent=2, default=str)

            # Create/overwrite blob
            await blob_client.upload_blob(
                content.encode('utf-8'),
                overwrite=True,
                metadata=metadata
            )

            logger.debug("ADLS save success", chat_id=chat_id)
            return True

        except Exception as e:
            logger.error("ADLS save failed", chat_id=chat_id, error=str(e))
            return False
    
    async def delete(self, chat_id: str) -> bool:
        """Delete chat from ADLS."""
        if not await self._ensure_connected():
            return False
        
        try:
            path = self._make_path(chat_id)
            blob_client = self._container_client.get_blob_client(path)
            await blob_client.delete_blob()
            logger.debug("ADLS delete success", chat_id=chat_id)
            return True
        except Exception as e:
            logger.warning("ADLS delete failed", chat_id=chat_id, error=str(e))
            return False
    
    async def exists(self, chat_id: str) -> bool:
        """Check if chat exists in ADLS."""
        if not await self._ensure_connected():
            return False
        
        try:
            path = self._make_path(chat_id)
            blob_client = self._container_client.get_blob_client(path)
            await blob_client.get_blob_properties()
            return True
        except Exception:
            return False
    
    async def list_chats(
        self, 
        prefix: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List persisted chats with metadata.
        
        Args:
            prefix: Optional prefix filter
            limit: Maximum number of results
            
        Returns:
            List of chat metadata dicts
        """
        if not await self._ensure_connected():
            return []
        
        try:
            folder = self.config.folder
            if prefix:
                folder = f"{folder}/{prefix}"
            
            results = []
            async for path in self._container_client.get_paths(path=folder):
                if path.name.endswith('.json'):
                    # Extract chat_id from path
                    chat_id = path.name.rsplit('/', 1)[-1].replace('.json', '')
                    results.append({
                        "chat_id": chat_id,
                        "path": path.name,
                        "size": path.content_length,
                        "last_modified": path.last_modified,
                        "persisted": True
                    })
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            logger.warning("ADLS list failed", error=str(e))
            return []
    
    async def get_metadata(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a chat without loading full data."""
        if not await self._ensure_connected():
            return None
        
        try:
            path = self._make_path(chat_id)
            file_client = self._container_client.get_file_client(path)
            props = await file_client.get_file_properties()
            
            return {
                "chat_id": chat_id,
                "size": props.size,
                "last_modified": props.last_modified,
                "persisted": True,
                "metadata": props.metadata
            }
        except Exception:
            return None
    
    def parse_schedule(self, cache_ttl: int) -> int:
        """
        Parse persist schedule and return seconds before TTL.
        
        Format: "ttl+SECONDS" means persist SECONDS before cache TTL expires.
        Example: cache_ttl=3600, schedule="ttl+300" -> persist at 3300s (300s before expiry)
        
        Args:
            cache_ttl: The cache TTL in seconds
            
        Returns:
            When to persist (in seconds from cache write)
        """
        schedule = self.config.schedule.strip().lower()
        
        if schedule.startswith("ttl+"):
            try:
                buffer = int(schedule.replace("ttl+", ""))
                return max(0, cache_ttl - buffer)
            except ValueError:
                logger.warning("Invalid persist schedule", schedule=schedule)
                return cache_ttl - 300  # Default 5 min buffer
        
        # Try parsing as absolute seconds
        try:
            return int(schedule)
        except ValueError:
            return cache_ttl - 300
    
    async def close(self) -> None:
        """Close ADLS connection and encryption client."""
        if self._encryption:
            await self._encryption.close()
            self._encryption = None

        if self._client:
            await self._client.close()
            self._client = None
            self._container_client = None
        logger.debug("ADLS persistence closed")
