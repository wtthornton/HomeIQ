"""
YAML Self-Correction Service
Implements iterative refinement with reverse engineering and similarity comparison
Based on 2025 research: Self-Refine, RPE, and ProActive Self-Refinement (PASR)
"""

import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
import yaml
import json
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """Result of one correction iteration"""
    iteration: int
    similarity_score: float
    original_prompt: str
    reverse_engineered_prompt: str
    yaml_content: str
    correction_feedback: str
    improvement_actions: List[str]


@dataclass
class SelfCorrectionResponse:
    """Final result after all iterations"""
    final_yaml: str
    final_similarity: float
    iterations_completed: int
    max_iterations: int
    convergence_achieved: bool
    iteration_history: List[CorrectionResult]
    total_tokens_used: int
    # Additional metrics for tracking (set after creation)
    initial_similarity: Optional[float] = None
    similarity_improvement: Optional[float] = None
    improvement_percentage: Optional[float] = None
    total_processing_time_ms: Optional[int] = None
    time_per_iteration_ms: Optional[float] = None
    original_yaml: Optional[str] = None
    yaml_changed: Optional[bool] = None


class YAMLSelfCorrectionService:
    """
    Self-correcting YAML generation with reverse engineering.
    
    Iterative Process:
    1. Generate YAML from prompt
    2. Reverse engineer YAML back to natural language
    3. Compare reverse-engineered text to original prompt
    4. Calculate semantic similarity
    5. Provide feedback and refine until convergence
    
    Based on research:
    - Self-Refine (arxiv.org/abs/2303.17651)
    - RPE - Reverse Prompt Engineering (learnprompting.org/docs/language-model-inversion/reverse-prompt-engineering)
    - PASR - ProActive Self-Refinement (arxiv.org/abs/2508.12903)
    """
    
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        model: str = "gpt-4o-mini",
        similarity_model: str = "all-MiniLM-L6-v2",
        ha_client: Optional[Any] = None,
        device_intelligence_client: Optional[Any] = None
    ):
        self.openai_client = openai_client
        self.model = model
        self.similarity_model_name = similarity_model
        self.ha_client = ha_client
        self.device_intelligence_client = device_intelligence_client
        
        # Load similarity model (cached for performance)
        self.similarity_model = SentenceTransformer(similarity_model)
        
        # Configuration
        self.max_iterations = 5
        self.min_similarity_threshold = 0.85  # 85% similarity target
        self.improvement_threshold = 0.02  # 2% minimum improvement per iteration
        
        logger.info(f"YAMLSelfCorrectionService initialized with model={model}, similarity_model={similarity_model}")
    
    async def correct_yaml(
        self,
        user_prompt: str,
        generated_yaml: str,
        context: Optional[Dict] = None,
        comprehensive_enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> SelfCorrectionResponse:
        """
        Main self-correction loop.
        
        Args:
            user_prompt: Original user request
            generated_yaml: Initial YAML to refine
            context: Optional context (devices, entities, etc.)
            comprehensive_enriched_data: Optional comprehensive enriched entity data
        
        Returns:
            SelfCorrectionResponse with refined YAML and history
        """
        logger.info(f"🔄 Starting self-correction for prompt: {user_prompt[:60]}...")
        
        # Track start time for performance metrics
        start_time = time.time()
        
        # Enhance context with comprehensive enriched data if available
        enhanced_context = context.copy() if context else {}
        if comprehensive_enriched_data:
            from .comprehensive_entity_enrichment import format_comprehensive_enrichment_for_prompt
            enhanced_context['comprehensive_entity_data'] = format_comprehensive_enrichment_for_prompt(comprehensive_enriched_data)
            logger.info(f"✅ Added comprehensive entity data to reverse engineering context ({len(comprehensive_enriched_data)} entities)")
        
        # Calculate INITIAL similarity (before reverse engineering) for comparison
        initial_similarity = 0.0
        initial_tokens = 0
        try:
            logger.info("📊 Calculating initial similarity (iteration 0)...")
            result = await self._reverse_engineer_yaml(
                generated_yaml,
                enhanced_context,
                comprehensive_enriched_data=comprehensive_enriched_data
            )
            # Handle both old format (string) and new format (tuple)
            if isinstance(result, tuple):
                initial_reverse_engineered, initial_tokens = result
            else:
                initial_reverse_engineered = result
                initial_tokens = 0
            
            initial_similarity = await self._calculate_similarity(user_prompt, initial_reverse_engineered)
            logger.info(f"📊 Initial similarity: {initial_similarity:.2%} (tokens: {initial_tokens})")
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate initial similarity: {e}")
        
        iteration_history: List[CorrectionResult] = []
        current_yaml = generated_yaml
        total_tokens = initial_tokens  # Include initial tokens
        previous_similarity = initial_similarity
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 Iteration {iteration}/{self.max_iterations}")
            
            # Step 1: Reverse engineer YAML to natural language (with comprehensive data)
            result = await self._reverse_engineer_yaml(
                current_yaml,
                enhanced_context,
                comprehensive_enriched_data=comprehensive_enriched_data
            )
            # Handle both old format (string) and new format (tuple)
            if isinstance(result, tuple):
                reverse_engineered_prompt, tokens_used = result
                total_tokens += tokens_used
            else:
                reverse_engineered_prompt = result
            
            # Step 2: Calculate semantic similarity
            similarity_score = await self._calculate_similarity(
                user_prompt,
                reverse_engineered_prompt
            )
            
            # Step 3: Check convergence
            improvement = similarity_score - previous_similarity
            
            logger.info(
                f"Iteration {iteration}: Similarity = {similarity_score:.2%}, "
                f"Improvement = {improvement:.2%}"
            )
            
            # Step 4: Store iteration result
            correction_result = CorrectionResult(
                iteration=iteration,
                similarity_score=similarity_score,
                original_prompt=user_prompt,
                reverse_engineered_prompt=reverse_engineered_prompt,
                yaml_content=current_yaml,
                correction_feedback="",
                improvement_actions=[]
            )
            
            # Step 5: Check if we should stop
            if similarity_score >= self.min_similarity_threshold:
                logger.info("✅ Target similarity achieved - stopping")
                correction_result.correction_feedback = (
                    f"Target similarity ({self.min_similarity_threshold:.0%}) achieved"
                )
                iteration_history.append(correction_result)
                break
            
            # Check if improvement is minimal
            if iteration > 1 and improvement < self.improvement_threshold:
                logger.warning(
                    f"⚠️ Minimal improvement ({improvement:.2%}) - near convergence"
                )
                correction_result.correction_feedback = (
                    "Minimal improvement detected - likely at optimal level"
                )
                iteration_history.append(correction_result)
                break
            
            # Step 6: Generate feedback and refine YAML
            feedback_and_actions, feedback_tokens = await self._generate_correction_feedback(
                user_prompt,
                reverse_engineered_prompt,
                similarity_score,
                current_yaml
            )
            total_tokens += feedback_tokens
            
            correction_result.correction_feedback = feedback_and_actions["feedback"]
            correction_result.improvement_actions = feedback_and_actions["actions"]
            
            # Step 7: Refine YAML based on feedback (with comprehensive data)
            if iteration < self.max_iterations:
                refined_yaml = await self._refine_yaml(
                    user_prompt,
                    current_yaml,
                    feedback_and_actions,
                    enhanced_context,
                    comprehensive_enriched_data=comprehensive_enriched_data
                )
                current_yaml = refined_yaml
            else:
                logger.info("Max iterations reached - using best result")
            
            previous_similarity = similarity_score
            iteration_history.append(correction_result)
        
        final_similarity = iteration_history[-1].similarity_score if iteration_history else initial_similarity
        
        # Calculate total processing time
        total_processing_time_ms = int((time.time() - start_time) * 1000)
        time_per_iteration_ms = total_processing_time_ms / len(iteration_history) if iteration_history else 0.0
        
        # Calculate similarity improvement
        similarity_improvement = final_similarity - initial_similarity
        improvement_percentage = ((final_similarity / initial_similarity - 1.0) * 100) if initial_similarity > 0 else 0.0
        
        logger.info(
            f"✅ Reverse engineering complete: "
            f"Similarity {initial_similarity:.2%} → {final_similarity:.2%} "
            f"(+{similarity_improvement:.2%}, {improvement_percentage:+.1f}%), "
            f"{len(iteration_history)} iterations, "
            f"{total_processing_time_ms}ms, "
            f"{total_tokens} tokens"
        )
        
        # Add initial similarity and timing to response (for metrics storage)
        response = SelfCorrectionResponse(
            final_yaml=current_yaml,
            final_similarity=final_similarity,
            iterations_completed=len(iteration_history),
            max_iterations=self.max_iterations,
            convergence_achieved=final_similarity >= self.min_similarity_threshold,
            iteration_history=iteration_history,
            total_tokens_used=total_tokens
        )
        
        # Attach additional metrics for tracking
        response.initial_similarity = initial_similarity
        response.similarity_improvement = similarity_improvement
        response.improvement_percentage = improvement_percentage
        response.total_processing_time_ms = total_processing_time_ms
        response.time_per_iteration_ms = time_per_iteration_ms
        response.original_yaml = generated_yaml
        response.final_yaml = current_yaml
        response.yaml_changed = (generated_yaml != current_yaml)
        
        return response
    
    def _extract_entity_ids_from_yaml(self, parsed_yaml: Dict) -> Set[str]:
        """
        Recursively extract all entity IDs from YAML structure.
        
        Searches in triggers, conditions, and actions (including nested structures).
        """
        entity_ids: Set[str] = set()
        
        def extract_from_value(value: Any):
            """Recursively extract entity_id values"""
            if isinstance(value, dict):
                # Check for entity_id key
                if 'entity_id' in value:
                    entity_id = value['entity_id']
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
                
                # Recursively check all values
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)
        
        # Extract from triggers
        triggers = parsed_yaml.get('trigger', [])
        if isinstance(triggers, list):
            for trigger in triggers:
                extract_from_value(trigger)
        
        # Extract from conditions
        conditions = parsed_yaml.get('condition', [])
        if isinstance(conditions, list):
            for condition in conditions:
                extract_from_value(condition)
        
        # Extract from actions
        actions = parsed_yaml.get('action', [])
        if isinstance(actions, list):
            for action in actions:
                extract_from_value(action)
        
        return entity_ids
    
    async def _get_device_friendly_names(self, entity_ids: Set[str]) -> Dict[str, str]:
        """
        Query device database to get friendly names for entity IDs.
        
        Returns a mapping of entity_id -> friendly_name.
        """
        entity_to_name: Dict[str, str] = {}
        
        if not entity_ids:
            return entity_to_name
        
        # Try HA client first (fastest - gets state with friendly_name attribute)
        if self.ha_client:
            try:
                from ..clients.ha_client import HomeAssistantClient
                
                # Fetch states for all entities at once if possible
                for entity_id in entity_ids:
                    try:
                        state = await self.ha_client.get_entity_state(entity_id)
                        if state:
                            # Try to get friendly_name from attributes
                            attributes = state.get('attributes', {})
                            friendly_name = attributes.get('friendly_name') or attributes.get('name')
                            if friendly_name:
                                entity_to_name[entity_id] = friendly_name
                                logger.debug(f"📋 Found friendly name from HA: {entity_id} -> {friendly_name}")
                    except Exception as e:
                        logger.debug(f"Could not get state for {entity_id}: {e}")
            except Exception as e:
                logger.debug(f"HA client lookup failed: {e}")
        
        # Fallback: Try device intelligence client
        if self.device_intelligence_client and len(entity_to_name) < len(entity_ids):
            try:
                from ..clients.device_intelligence_client import DeviceIntelligenceClient
                
                # Get all devices and match by entity
                all_devices = await self.device_intelligence_client.get_all_devices(limit=500)
                
                for entity_id in entity_ids:
                    if entity_id in entity_to_name:
                        continue  # Already found
                    
                    # Try to find device that matches this entity
                    for device in all_devices:
                        if isinstance(device, dict):
                            device_entities = device.get('entities', []) or device.get('entity_ids', [])
                            if entity_id in device_entities:
                                friendly_name = device.get('friendly_name') or device.get('name') or device.get('device_name')
                                if friendly_name:
                                    entity_to_name[entity_id] = friendly_name
                                    logger.debug(f"📋 Found friendly name from device DB: {entity_id} -> {friendly_name}")
                                    break
            except Exception as e:
                logger.debug(f"Device intelligence lookup failed: {e}")
        
        # Use entity_id as fallback name if no friendly name found
        for entity_id in entity_ids:
            if entity_id not in entity_to_name:
                # Use a readable version of entity_id (e.g., "light.office" -> "office light")
                domain, name = entity_id.split('.', 1) if '.' in entity_id else (entity_id, '')
                readable_name = name.replace('_', ' ').title() if name else entity_id
                entity_to_name[entity_id] = readable_name
        
        logger.info(f"📋 Resolved {len(entity_to_name)}/{len(entity_ids)} entity friendly names for reverse engineering")
        return entity_to_name
    
    async def _reverse_engineer_yaml(
        self,
        yaml_content: str,
        context: Optional[Dict] = None,
        comprehensive_enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> tuple[str, int]:
        """
        Reverse engineer YAML back to natural language description.
        
        Uses Reverse Prompt Engineering (RPE) techniques to reconstruct intent.
        Now includes device database lookup for accurate device names.
        """
        # Parse YAML to extract key information
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in reverse engineering: {e}")
            return "Invalid YAML configuration"
        
        if not parsed_yaml:
            return "Empty YAML configuration"
        
        # Extract all entity IDs from YAML
        entity_ids = self._extract_entity_ids_from_yaml(parsed_yaml)
        logger.debug(f"🔍 Extracted {len(entity_ids)} entity IDs from YAML: {list(entity_ids)[:5]}")
        
        # Query device database for friendly names AND comprehensive data
        entity_friendly_names = await self._get_device_friendly_names(entity_ids)
        
        # Build comprehensive device information section using enriched data if available
        device_info_section = ""
        
        if comprehensive_enriched_data:
            # Use comprehensive enrichment data (includes capabilities, health, manufacturer, model, area, etc.)
            from .comprehensive_entity_enrichment import format_comprehensive_enrichment_for_prompt
            comprehensive_info = format_comprehensive_enrichment_for_prompt(comprehensive_enriched_data)
            device_info_section = f"\n\nCOMPREHENSIVE DEVICE/ENTITY INFORMATION (use this data for accurate descriptions):\n{comprehensive_info}\n\nWhen describing devices, use their friendly names and include relevant details like location, capabilities, and health status."
        elif entity_friendly_names:
            # Fallback to basic friendly name mapping
            device_mappings = []
            for entity_id, friendly_name in entity_friendly_names.items():
                device_mappings.append(f"  - {entity_id} → {friendly_name}")
            
            device_info_section = f"\n\nDevice/Entity Mappings (use these friendly names in your description):\n" + "\n".join(device_mappings)
        
        device_names_section = device_info_section  # For backwards compatibility
        
        # Build prompt for OpenAI reverse engineering with comprehensive data
        context_section = ""
        if context:
            context_section = f"\n\nAdditional Context:\n{self._format_context(context)}"
        
        # Add comprehensive entity data to context if available
        comprehensive_data_section = ""
        if comprehensive_enriched_data:
            from .comprehensive_entity_enrichment import format_comprehensive_enrichment_for_prompt
            comprehensive_data_section = f"\n\nCOMPREHENSIVE ENTITY DATA:\n{format_comprehensive_enrichment_for_prompt(comprehensive_enriched_data)}"
        
        reverse_engineering_prompt = f"""Analyze this Home Assistant automation YAML and describe what it does in natural language.

YAML:
```yaml
{yaml_content}
```
{device_names_section}{comprehensive_data_section}{context_section}

Your task: Write a clear, concise paragraph describing:
1. What trigger starts this automation
2. What conditions must be met (if any)
3. What actions are performed
4. Any special features (delays, repeats, sequences, etc.)

IMPORTANT: 
- Use the friendly device names and comprehensive data from above (e.g., "Office Light" instead of "light.office")
- Include relevant device details when appropriate (location, capabilities, manufacturer, model)
- This makes the description more natural and matches how users think about their devices
- Reference device capabilities and health status when relevant

Write as if explaining to a user who asked for this automation."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant expert who explains automations clearly in plain English using friendly device names."
                    },
                    {
                        "role": "user",
                        "content": reverse_engineering_prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=300
            )
            
            # Track tokens
            usage = response.usage
            tokens_used = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
            
            reverse_description = response.choices[0].message.content.strip()
            logger.debug(f"Reverse engineered: {reverse_description[:100]}... (tokens: {tokens_used})")
            return reverse_description, tokens_used
            
        except Exception as e:
            logger.error(f"Reverse engineering failed: {e}")
            return "Failed to analyze YAML", 0
    
    async def _calculate_similarity(
        self,
        original_prompt: str,
        reverse_engineered: str
    ) -> float:
        """
        Calculate semantic similarity between two texts using embeddings.
        
        Uses SentenceTransformers for fast, accurate comparison.
        """
        try:
            # Generate embeddings
            embeddings = self.similarity_model.encode(
                [original_prompt, reverse_engineered]
            )
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity_matrix = cosine_similarity(
                embeddings[0:1],
                embeddings[1:2]
            )
            
            similarity_score = float(similarity_matrix[0][0])
            
            # Clip to valid range
            similarity_score = max(0.0, min(1.0, similarity_score))
            
            logger.debug(f"Similarity score: {similarity_score:.4f}")
            return similarity_score
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    async def _generate_correction_feedback(
        self,
        original_prompt: str,
        reverse_engineered: str,
        similarity_score: float,
        current_yaml: str
    ) -> tuple[Dict[str, List[str]], int]:
        """
        Generate actionable feedback for improving YAML.
        
        Uses ProActive Self-Refinement (PASR) techniques.
        """
        feedback_prompt = f"""Analyze why these two descriptions differ and provide actionable corrections.

Original Request:
"{original_prompt}"

What the YAML Actually Does:
"{reverse_engineered}"

Current Similarity: {similarity_score:.2%}

Your task:
1. Identify the key differences
2. Explain why they differ (missing features, wrong interpretation, etc.)
3. Provide specific actions to align the YAML with the original request

Format your response as:
FEEDBACK: [brief explanation of main issues]
ACTION 1: [specific change needed]
ACTION 2: [specific change needed]
..."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying discrepancies in automation logic and providing precise corrections."
                    },
                    {
                        "role": "user",
                        "content": feedback_prompt
                    }
                ],
                temperature=0.5,
                max_tokens=400
            )
            
            # Track tokens (will be added to total_tokens by caller)
            usage = response.usage
            tokens_used = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
            
            feedback_text = response.choices[0].message.content
            
            # Parse feedback and actions
            feedback = ""
            actions = []
            
            lines = feedback_text.split("\n")
            for line in lines:
                if line.startswith("FEEDBACK:"):
                    feedback = line.replace("FEEDBACK:", "").strip()
                elif line.startswith("ACTION"):
                    action = line.split(":", 1)[-1].strip()
                    actions.append(action)
            
            return {
                "feedback": feedback or "No specific feedback generated",
                "actions": actions if actions else ["Review and adjust YAML manually"]
            }, tokens_used
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return {
                "feedback": f"Error generating feedback: {str(e)}",
                "actions": ["Manual review recommended"]
            }, 0
    
    async def _refine_yaml(
        self,
        original_prompt: str,
        current_yaml: str,
        feedback: Dict[str, List[str]],
        context: Optional[Dict] = None,
        comprehensive_enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> tuple[str, int]:
        """
        Refine YAML based on feedback.
        
        Uses the feedback to generate improved YAML that better matches the original intent.
        """
        context_section = ""
        if context:
            context_section = f"\n\nAdditional Context:\n{self._format_context(context)}"
        
        # Add comprehensive entity data to refinement context
        comprehensive_data_section = ""
        if comprehensive_enriched_data:
            from .comprehensive_entity_enrichment import format_comprehensive_enrichment_for_prompt
            comprehensive_data_section = f"\n\nCOMPREHENSIVE ENTITY DATA:\n{format_comprehensive_enrichment_for_prompt(comprehensive_enriched_data)}"
        
        actions_list = "\n".join([f"- {action}" for action in feedback["actions"]])
        
        refinement_prompt = f"""Refine this Home Assistant automation YAML to better match the original request.

Original Request:
"{original_prompt}"

Current YAML:
```yaml
{current_yaml}
```

Feedback:
{feedback['feedback']}

Required Changes:
{actions_list}
{comprehensive_data_section}{context_section}

Generate the improved YAML that addresses these issues while maintaining valid Home Assistant syntax."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant expert who refines YAML automations based on feedback."
                    },
                    {
                        "role": "user",
                        "content": refinement_prompt
                    }
                ],
                temperature=0.2,  # Low temperature for consistency
                max_tokens=1500
            )
            
            # Track tokens
            usage = response.usage
            tokens_used = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
            
            refined_yaml_text = response.choices[0].message.content.strip()
            
            # Extract YAML from markdown code block if present
            if "```yaml" in refined_yaml_text:
                refined_yaml_text = refined_yaml_text.split("```yaml")[1].split("```")[0].strip()
            elif "```" in refined_yaml_text:
                refined_yaml_text = refined_yaml_text.split("```")[1].split("```")[0].strip()
            
            # Validate YAML syntax
            try:
                yaml.safe_load(refined_yaml_text)
                logger.debug("Refined YAML syntax is valid")
            except yaml.YAMLError as e:
                logger.error(f"Refined YAML has syntax error: {e}")
                return current_yaml, 0  # Return original if refinement is invalid
            
            return refined_yaml_text, tokens_used
            
        except Exception as e:
            logger.error(f"YAML refinement failed: {e}")
            return current_yaml, 0
    
    def _format_context(self, context: Dict) -> str:
        """Format context dict for prompts"""
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

