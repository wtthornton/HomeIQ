"""
Home Assistant Requests Dataset Loader

Loads and preprocesses the Home Assistant Requests dataset from Hugging Face
for fine-tuning NLP models on smart home command understanding.

Dataset: acon96/Home-Assistant-Requests
- User requests + assistant responses for Home Assistant control
- Includes intent classification and entity extraction labels
"""

import json
import logging
from pathlib import Path
from typing import Any, Iterator

import polars as pl

logger = logging.getLogger(__name__)


# Home Assistant intent types
HA_INTENT_TYPES = {
    "HassTurnOn": "Turn on a device",
    "HassTurnOff": "Turn off a device",
    "HassToggle": "Toggle a device",
    "HassSetPosition": "Set position (covers, blinds)",
    "HassSetBrightness": "Set light brightness",
    "HassSetColor": "Set light color",
    "HassSetTemperature": "Set thermostat temperature",
    "HassGetState": "Get device state",
    "HassListDevices": "List devices",
    "HassActivateScene": "Activate a scene",
    "HassRunScript": "Run a script",
    "HassNevermind": "Cancel/nevermind",
    "HassHelp": "Help request",
}

# Entity type mappings
HA_ENTITY_TYPES = {
    "name": "Device name",
    "area": "Area/room name",
    "domain": "Device domain (light, switch, etc.)",
    "device_class": "Device class (motion, door, etc.)",
    "brightness": "Brightness value",
    "color": "Color value",
    "temperature": "Temperature value",
    "position": "Position value",
}


class HARequestsLoader:
    """
    Load and preprocess Home Assistant Requests dataset for fine-tuning.
    
    This loader:
    1. Loads the dataset from Hugging Face
    2. Structures data for different fine-tuning approaches:
       - OpenAI fine-tuning (JSONL format)
       - PEFT/LoRA fine-tuning (prompt-completion pairs)
       - Intent classification
       - Entity extraction
    """
    
    def __init__(
        self,
        cache_dir: Path | None = None,
        streaming: bool = False,
    ):
        """
        Initialize the HA Requests loader.
        
        Args:
            cache_dir: Directory to cache downloaded data
            streaming: Whether to stream dataset (for large data)
        """
        self.cache_dir = cache_dir or Path("./data/ha_requests_cache")
        self.streaming = streaming
        self._dataset = None
    
    def load(self) -> pl.DataFrame:
        """
        Load and preprocess the Home Assistant Requests dataset.
        
        Returns:
            Polars DataFrame with preprocessed data including:
            - prompt: User request text
            - completion: Assistant response
            - intent: Intent classification label
            - entities: Extracted entities as JSON string
            - domain: Target device domain
            - area: Target area/room
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "Please install the datasets library: pip install datasets>=3.0.0"
            )
        
        logger.info("Loading Home Assistant Requests dataset from Hugging Face...")
        
        # Load dataset
        dataset = load_dataset(
            "acon96/Home-Assistant-Requests",
            cache_dir=str(self.cache_dir),
        )
        
        self._dataset = dataset
        
        # Convert to Polars DataFrame
        df = pl.from_arrow(dataset["train"].data.table)
        
        logger.info(f"Loaded {len(df):,} training examples")
        
        # Preprocess
        df = self._preprocess(df)
        
        return df
    
    def _preprocess(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Preprocess the raw dataset.
        
        Args:
            df: Raw Polars DataFrame
            
        Returns:
            Preprocessed DataFrame
        """
        logger.info("Preprocessing Home Assistant Requests data...")
        
        columns = df.columns
        
        # Identify columns (dataset structure may vary)
        prompt_col = self._find_column(columns, ["request", "user_request", "prompt", "input"])
        response_col = self._find_column(columns, ["response", "assistant_response", "completion", "output"])
        intent_col = self._find_column(columns, ["intent", "intent_type", "label"])
        entities_col = self._find_column(columns, ["entities", "slots", "extracted_entities"])
        
        expressions = []
        
        # Standardize column names
        if prompt_col:
            expressions.append(pl.col(prompt_col).alias("prompt"))
        
        if response_col:
            expressions.append(pl.col(response_col).alias("completion"))
        
        if intent_col:
            expressions.append(pl.col(intent_col).alias("intent"))
        
        if entities_col:
            # Ensure entities are stored as JSON string
            expressions.append(
                pl.col(entities_col)
                .map_elements(
                    lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x),
                    return_dtype=pl.Utf8
                )
                .alias("entities")
            )
        
        if expressions:
            df = df.with_columns(expressions)
        
        # Extract domain and area from entities if available
        if "entities" in df.columns:
            df = df.with_columns([
                pl.col("entities")
                .map_elements(self._extract_domain, return_dtype=pl.Utf8)
                .alias("domain"),
                pl.col("entities")
                .map_elements(self._extract_area, return_dtype=pl.Utf8)
                .alias("area"),
            ])
        
        logger.info(f"Preprocessed {len(df):,} examples with {len(df.columns)} columns")
        
        return df
    
    def _find_column(self, columns: list[str], candidates: list[str]) -> str | None:
        """Find a column by checking multiple candidate names."""
        for candidate in candidates:
            for col in columns:
                if candidate.lower() in col.lower():
                    return col
        return None
    
    def _extract_domain(self, entities_json: str) -> str:
        """Extract domain from entities JSON."""
        try:
            entities = json.loads(entities_json) if isinstance(entities_json, str) else entities_json
            if isinstance(entities, dict):
                return entities.get("domain", "")
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and "domain" in entity:
                        return entity["domain"]
        except (json.JSONDecodeError, TypeError):
            pass
        return ""
    
    def _extract_area(self, entities_json: str) -> str:
        """Extract area from entities JSON."""
        try:
            entities = json.loads(entities_json) if isinstance(entities_json, str) else entities_json
            if isinstance(entities, dict):
                return entities.get("area", "")
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and "area" in entity:
                        return entity["area"]
        except (json.JSONDecodeError, TypeError):
            pass
        return ""
    
    def to_openai_format(
        self,
        df: pl.DataFrame,
        system_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Convert dataset to OpenAI fine-tuning format.
        
        Args:
            df: Preprocessed DataFrame
            system_prompt: Optional system prompt to include
            
        Returns:
            List of conversation dictionaries for OpenAI fine-tuning
        """
        if system_prompt is None:
            system_prompt = (
                "You are a Home Assistant AI that helps users control their smart home. "
                "Parse user requests and generate appropriate Home Assistant service calls. "
                "Be precise with entity names, areas, and parameters."
            )
        
        examples = []
        
        for row in df.iter_rows(named=True):
            prompt = row.get("prompt", "")
            completion = row.get("completion", "")
            
            if not prompt or not completion:
                continue
            
            example = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": completion},
                ]
            }
            examples.append(example)
        
        logger.info(f"Converted {len(examples):,} examples to OpenAI format")
        
        return examples
    
    def to_peft_format(
        self,
        df: pl.DataFrame,
        instruction_template: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Convert dataset to PEFT/LoRA fine-tuning format.
        
        Args:
            df: Preprocessed DataFrame
            instruction_template: Template for instruction-tuning format
            
        Returns:
            List of instruction-input-output dictionaries
        """
        if instruction_template is None:
            instruction_template = (
                "You are a Home Assistant AI. Parse the user's smart home request "
                "and generate the appropriate response or service call."
            )
        
        examples = []
        
        for row in df.iter_rows(named=True):
            prompt = row.get("prompt", "")
            completion = row.get("completion", "")
            
            if not prompt or not completion:
                continue
            
            example = {
                "instruction": instruction_template,
                "input": prompt,
                "output": completion,
            }
            examples.append(example)
        
        logger.info(f"Converted {len(examples):,} examples to PEFT format")
        
        return examples
    
    def to_intent_classification_format(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Convert dataset to intent classification format.
        
        Args:
            df: Preprocessed DataFrame
            
        Returns:
            DataFrame with text and label columns for classification
        """
        if "intent" not in df.columns:
            raise ValueError("DataFrame must have 'intent' column")
        
        # Filter rows with valid intents
        classification_df = df.filter(
            pl.col("intent").is_not_null() & (pl.col("intent") != "")
        ).select([
            pl.col("prompt").alias("text"),
            pl.col("intent").alias("label"),
        ])
        
        logger.info(f"Created intent classification dataset with {len(classification_df):,} examples")
        
        return classification_df
    
    def save_openai_jsonl(
        self,
        examples: list[dict[str, Any]],
        output_path: Path | str,
    ) -> None:
        """Save examples in OpenAI JSONL format."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
        
        logger.info(f"Saved {len(examples):,} examples to {output_path}")
    
    def save_processed(self, df: pl.DataFrame, output_path: Path | str) -> None:
        """Save processed data to Parquet."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.write_parquet(output_path)
        logger.info(f"Saved processed data to {output_path}")
    
    def load_processed(self, input_path: Path | str) -> pl.DataFrame:
        """Load previously processed data from Parquet."""
        return pl.read_parquet(input_path)
    
    def get_intent_distribution(self, df: pl.DataFrame) -> pl.DataFrame:
        """Get distribution of intents in the dataset."""
        if "intent" not in df.columns:
            raise ValueError("DataFrame must have 'intent' column")
        
        return (
            df
            .group_by("intent")
            .agg([
                pl.count().alias("count"),
            ])
            .sort("count", descending=True)
        )
    
    def get_domain_distribution(self, df: pl.DataFrame) -> pl.DataFrame:
        """Get distribution of domains in the dataset."""
        if "domain" not in df.columns:
            raise ValueError("DataFrame must have 'domain' column")
        
        return (
            df
            .filter(pl.col("domain") != "")
            .group_by("domain")
            .agg([
                pl.count().alias("count"),
            ])
            .sort("count", descending=True)
        )
    
    def split_dataset(
        self,
        df: pl.DataFrame,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        seed: int = 42,
    ) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """
        Split dataset into train/validation/test sets.
        
        Args:
            df: DataFrame to split
            train_ratio: Ratio for training set
            val_ratio: Ratio for validation set
            seed: Random seed
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        # Shuffle
        df = df.sample(fraction=1.0, seed=seed)
        
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        train_df = df[:train_end]
        val_df = df[train_end:val_end]
        test_df = df[val_end:]
        
        logger.info(
            f"Split dataset: train={len(train_df):,}, "
            f"val={len(val_df):,}, test={len(test_df):,}"
        )
        
        return train_df, val_df, test_df


def main():
    """Example usage of HARequestsLoader."""
    logging.basicConfig(level=logging.INFO)
    
    loader = HARequestsLoader()
    
    # Load and preprocess
    df = loader.load()
    print(f"\nLoaded {len(df):,} examples")
    print(f"Columns: {df.columns}")
    print(f"\nSample data:\n{df.head()}")
    
    # Get distributions
    if "intent" in df.columns:
        intent_dist = loader.get_intent_distribution(df)
        print(f"\nIntent distribution:\n{intent_dist}")
    
    if "domain" in df.columns:
        domain_dist = loader.get_domain_distribution(df)
        print(f"\nDomain distribution:\n{domain_dist}")
    
    # Convert to OpenAI format
    openai_examples = loader.to_openai_format(df)
    print(f"\nOpenAI format example:\n{json.dumps(openai_examples[0], indent=2)}")
    
    # Save for OpenAI fine-tuning
    loader.save_openai_jsonl(openai_examples, "data/ha_requests_openai.jsonl")


if __name__ == "__main__":
    main()
