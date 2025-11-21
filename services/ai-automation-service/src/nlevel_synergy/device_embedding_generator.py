"""
Device Embedding Generator

Epic AI-4, Story AI4.1: Device Embedding Generation
Main orchestrator for generating and managing device embeddings.

Responsibilities:
- Fetch devices and entities from data-api
- Generate natural language descriptors
- Create semantic embeddings using OpenVINO INT8 model
- Store embeddings in database with 30-day caching
- Batch processing for efficiency
"""

import logging
from datetime import datetime, timedelta

import numpy as np

logger = logging.getLogger(__name__)


class DeviceEmbeddingGenerator:
    """
    Generates and manages device embeddings for n-level synergy detection.

    Story AI4.1: Device Embedding Generation

    Features:
    - Batch processing (32 devices at a time)
    - 30-day caching to avoid unnecessary regeneration
    - Graceful error handling for individual devices
    - Integration with device capabilities

    Usage:
        >>> generator = DeviceEmbeddingGenerator(db_session, data_api_client, capability_service)
        >>> stats = await generator.generate_all_embeddings()
        >>> print(stats)
        {'total_devices': 20, 'generated': 5, 'cached': 15, 'errors': 0}
    """

    def __init__(
        self,
        db_session,
        data_api_client,
        capability_service,
        cache_days: int = 30,
    ):
        """
        Initialize embedding generator.

        Args:
            db_session: SQLite database session
            data_api_client: Client for fetching devices/entities
            capability_service: Service for fetching device capabilities
            cache_days: Number of days to cache embeddings (default: 30)
        """
        self.db = db_session
        self.data_api = data_api_client
        self.capability_service = capability_service
        self.cache_days = cache_days

        # Initialize components
        from .descriptor_builder import DeviceDescriptorBuilder
        from .embedding_model import DeviceEmbeddingModel

        self.descriptor_builder = DeviceDescriptorBuilder(capability_service)
        self.embedding_model = DeviceEmbeddingModel()

        # Load model on initialization
        logger.info("Initializing DeviceEmbeddingGenerator...")
        self.embedding_model.load_model()

        logger.info(
            f"DeviceEmbeddingGenerator initialized: cache_days={cache_days}",
        )

    async def generate_all_embeddings(
        self,
        force_refresh: bool = False,
    ) -> dict:
        """
        Generate embeddings for all devices.

        Process:
        1. Fetch all devices and entities from data-api
        2. Check cache (skip if fresh and not force_refresh)
        3. Generate descriptors for devices needing update
        4. Batch generate embeddings (32 at a time)
        5. Store in database
        6. Return statistics

        Args:
            force_refresh: If True, regenerate even if cached

        Returns:
            Statistics dict with:
            - total_devices: Total number of devices processed
            - generated: Number of embeddings generated
            - cached: Number of embeddings from cache
            - errors: Number of failures
            - generation_time_ms: Time taken in milliseconds

        Example:
            >>> stats = await generator.generate_all_embeddings()
            >>> print(f"Generated {stats['generated']} new embeddings")
        """
        logger.info("🔧 Starting device embedding generation...")
        start_time = datetime.utcnow()

        stats = {
            "total_devices": 0,
            "generated": 0,
            "cached": 0,
            "errors": 0,
            "generation_time_ms": 0,
        }

        try:
            # Step 1: Get all devices and entities
            logger.info("📦 Fetching devices and entities from data-api...")
            devices = await self.data_api.fetch_devices()
            entities = await self.data_api.fetch_entities()

            stats["total_devices"] = len(entities)
            logger.info(f"Found {len(devices)} devices, {len(entities)} entities")

            # Create entity lookup for performance
            {e["entity_id"]: e for e in entities}
            device_map = {d.get("device_id"): d for d in devices if d.get("device_id")}

            # Step 2: Prepare device descriptors (check cache)
            descriptors_to_generate = []
            entity_ids_to_generate = []
            devices_to_generate = []

            for entity in entities:
                entity_id = entity["entity_id"]

                # Check cache (skip if fresh and not force_refresh)
                if not force_refresh and self._is_cached(entity_id):
                    stats["cached"] += 1
                    logger.debug(f"✅ Cached: {entity_id}")
                    continue

                # Get device and capabilities
                device_id = entity.get("device_id")
                device = device_map.get(device_id) if device_id else None

                # Fetch capabilities (may be None if device has no capabilities)
                capabilities = None
                if device and device_id:
                    try:
                        capabilities = await self.capability_service.get_capabilities(device_id)
                    except Exception as e:
                        logger.debug(f"No capabilities for {device_id}: {e}")

                # Generate descriptor
                try:
                    descriptor = self.descriptor_builder.create_descriptor(
                        device=device or {},
                        entity=entity,
                        capabilities=capabilities,
                    )

                    descriptors_to_generate.append(descriptor)
                    entity_ids_to_generate.append(entity_id)
                    devices_to_generate.append({
                        "entity_id": entity_id,
                        "device_id": device_id,
                        "descriptor": descriptor,
                    })

                    logger.debug(f"📝 Descriptor: {entity_id} -> {descriptor}")

                except Exception as e:
                    logger.exception(f"Failed to create descriptor for {entity_id}: {e}")
                    stats["errors"] += 1

            # Step 3: Batch generate embeddings
            if descriptors_to_generate:
                logger.info(f"🤖 Generating embeddings for {len(descriptors_to_generate)} devices...")

                try:
                    # Batch encoding (Context7 best practice: batch_size=32)
                    embeddings = self.embedding_model.encode(
                        descriptors_to_generate,
                        batch_size=32,
                        normalize=True,  # For dot-product similarity
                        convert_to_numpy=True,
                    )

                    logger.info(f"✅ Generated {len(embeddings)} embeddings (shape: {embeddings.shape})")

                    # Step 4: Store in database
                    model_info = self.embedding_model.get_model_info()

                    for _i, (entity_id, descriptor, embedding) in enumerate(
                        zip(entity_ids_to_generate, descriptors_to_generate, embeddings, strict=False),
                    ):
                        try:
                            self._store_embedding(
                                entity_id=entity_id,
                                embedding=embedding,
                                descriptor=descriptor,
                                model_version=model_info["model_version"],
                            )
                            stats["generated"] += 1

                        except Exception as e:
                            logger.exception(f"Failed to store embedding for {entity_id}: {e}")
                            stats["errors"] += 1

                    logger.info(f"💾 Stored {stats['generated']} embeddings in database")

                except Exception as e:
                    logger.error(f"Batch embedding generation failed: {e}", exc_info=True)
                    stats["errors"] += len(descriptors_to_generate)

            else:
                logger.info("✅ All embeddings are cached (no generation needed)")

            # Calculate statistics
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            stats["generation_time_ms"] = int(duration)

            # Log summary
            logger.info(
                f"✅ Embedding generation complete:\n"
                f"   Total devices: {stats['total_devices']}\n"
                f"   Generated: {stats['generated']}\n"
                f"   Cached: {stats['cached']}\n"
                f"   Errors: {stats['errors']}\n"
                f"   Time: {stats['generation_time_ms']}ms ({duration/1000:.2f}s)",
            )

            return stats

        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}", exc_info=True)
            raise

    def _is_cached(self, entity_id: str) -> bool:
        """
        Check if embedding is cached and fresh.

        Args:
            entity_id: Entity identifier

        Returns:
            True if cached and fresh, False otherwise
        """
        try:
            result = self.db.execute(
                "SELECT last_updated, model_version FROM device_embeddings WHERE entity_id = ?",
                (entity_id,),
            ).fetchone()

            if not result:
                return False

            last_updated_str, model_version = result

            # Check version match
            current_version = self.embedding_model.get_model_info()["model_version"]
            if model_version != current_version:
                logger.debug(f"Version mismatch for {entity_id}: {model_version} != {current_version}")
                return False

            # Check freshness
            last_updated = datetime.fromisoformat(last_updated_str)
            age = datetime.utcnow() - last_updated
            is_fresh = age < timedelta(days=self.cache_days)

            if not is_fresh:
                logger.debug(f"Stale cache for {entity_id}: {age.days} days old")

            return is_fresh

        except Exception as e:
            logger.exception(f"Cache check failed for {entity_id}: {e}")
            return False

    def _store_embedding(
        self,
        entity_id: str,
        embedding: np.ndarray,
        descriptor: str,
        model_version: str,
    ):
        """
        Store embedding in database.

        Args:
            entity_id: Entity identifier
            embedding: Embedding vector (384-dim numpy array)
            descriptor: Natural language description
            model_version: Model version string
        """
        # Calculate L2 norm for validation
        embedding_norm = float(np.linalg.norm(embedding))

        # Serialize embedding to bytes
        embedding_bytes = embedding.tobytes()

        # Upsert (insert or update)
        self.db.execute(
            """
            INSERT INTO device_embeddings
            (entity_id, embedding, descriptor, model_version, embedding_norm, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                embedding = excluded.embedding,
                descriptor = excluded.descriptor,
                model_version = excluded.model_version,
                embedding_norm = excluded.embedding_norm,
                last_updated = excluded.last_updated
            """,
            (
                entity_id,
                embedding_bytes,
                descriptor,
                model_version,
                embedding_norm,
                datetime.utcnow().isoformat(),
            ),
        )
        self.db.commit()

        logger.debug(
            f"Stored embedding for {entity_id}: "
            f"norm={embedding_norm:.4f}, "
            f"version={model_version}",
        )

    def get_embedding(self, entity_id: str) -> np.ndarray | None:
        """
        Retrieve embedding for a single entity.

        Args:
            entity_id: Entity identifier

        Returns:
            Embedding as numpy array, or None if not found
        """
        try:
            result = self.db.execute(
                "SELECT embedding FROM device_embeddings WHERE entity_id = ?",
                (entity_id,),
            ).fetchone()

            if result:
                embedding_bytes = result[0]
                return np.frombuffer(embedding_bytes, dtype=np.float32)

            return None

        except Exception as e:
            logger.exception(f"Failed to retrieve embedding for {entity_id}: {e}")
            return None

    def get_all_embeddings(self) -> dict[str, np.ndarray]:
        """
        Retrieve all embeddings from database.

        Returns:
            Dict mapping entity_id to embedding array
        """
        try:
            results = self.db.execute(
                "SELECT entity_id, embedding FROM device_embeddings",
            ).fetchall()

            embeddings = {}
            for entity_id, embedding_bytes in results:
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                embeddings[entity_id] = embedding

            logger.info(f"Retrieved {len(embeddings)} embeddings from database")
            return embeddings

        except Exception as e:
            logger.exception(f"Failed to retrieve all embeddings: {e}")
            return {}

    def get_stats(self) -> dict:
        """
        Get embedding generation statistics.

        Returns:
            Dict with statistics:
            - total_embeddings: Total embeddings in database
            - model_version: Current model version
            - oldest_embedding: Age of oldest embedding in days
            - newest_embedding: Age of newest embedding in days
        """
        try:
            # Count total
            result = self.db.execute(
                "SELECT COUNT(*) FROM device_embeddings",
            ).fetchone()
            total = result[0] if result else 0

            # Get age range
            result = self.db.execute(
                "SELECT MIN(last_updated), MAX(last_updated) FROM device_embeddings",
            ).fetchone()

            stats = {
                "total_embeddings": total,
                "model_version": self.embedding_model.get_model_info()["model_version"],
            }

            if result and result[0]:
                oldest_str, newest_str = result
                oldest = datetime.fromisoformat(oldest_str)
                newest = datetime.fromisoformat(newest_str)
                now = datetime.utcnow()

                stats["oldest_embedding_days"] = (now - oldest).days
                stats["newest_embedding_days"] = (now - newest).days

            return stats

        except Exception as e:
            logger.exception(f"Failed to get stats: {e}")
            return {"total_embeddings": 0, "model_version": "unknown"}

