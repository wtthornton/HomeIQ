"""
YAML Self-Correction Service
Implements iterative refinement with reverse engineering and similarity comparison
Based on 2025 research: Self-Refine, RPE, and ProActive Self-Refinement (PASR)
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import yaml
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
        similarity_model: str = "all-MiniLM-L6-v2"
    ):
        self.openai_client = openai_client
        self.model = model
        self.similarity_model_name = similarity_model
        
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
        context: Optional[Dict] = None
    ) -> SelfCorrectionResponse:
        """
        Main self-correction loop.
        
        Args:
            user_prompt: Original user request
            generated_yaml: Initial YAML to refine
            context: Optional context (devices, entities, etc.)
        
        Returns:
            SelfCorrectionResponse with refined YAML and history
        """
        logger.info(f"🔄 Starting self-correction for prompt: {user_prompt[:60]}...")
        
        iteration_history: List[CorrectionResult] = []
        current_yaml = generated_yaml
        total_tokens = 0
        previous_similarity = 0.0
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 Iteration {iteration}/{self.max_iterations}")
            
            # Step 1: Reverse engineer YAML to natural language
            reverse_engineered_prompt = await self._reverse_engineer_yaml(
                current_yaml,
                context
            )
            
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
            feedback_and_actions = await self._generate_correction_feedback(
                user_prompt,
                reverse_engineered_prompt,
                similarity_score,
                current_yaml
            )
            
            correction_result.correction_feedback = feedback_and_actions["feedback"]
            correction_result.improvement_actions = feedback_and_actions["actions"]
            
            # Step 7: Refine YAML based on feedback
            if iteration < self.max_iterations:
                refined_yaml = await self._refine_yaml(
                    user_prompt,
                    current_yaml,
                    feedback_and_actions,
                    context
                )
                current_yaml = refined_yaml
            else:
                logger.info("Max iterations reached - using best result")
            
            previous_similarity = similarity_score
            iteration_history.append(correction_result)
        
        final_similarity = iteration_history[-1].similarity_score if iteration_history else 0.0
        
        return SelfCorrectionResponse(
            final_yaml=current_yaml,
            final_similarity=final_similarity,
            iterations_completed=len(iteration_history),
            max_iterations=self.max_iterations,
            convergence_achieved=final_similarity >= self.min_similarity_threshold,
            iteration_history=iteration_history,
            total_tokens_used=total_tokens
        )
    
    async def _reverse_engineer_yaml(
        self,
        yaml_content: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Reverse engineer YAML back to natural language description.
        
        Uses Reverse Prompt Engineering (RPE) techniques to reconstruct intent.
        """
        # Parse YAML to extract key information
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in reverse engineering: {e}")
            return "Invalid YAML configuration"
        
        # Build prompt for OpenAI reverse engineering
        context_section = ""
        if context:
            context_section = f"\n\nAdditional Context:\n{self._format_context(context)}"
        
        reverse_engineering_prompt = f"""Analyze this Home Assistant automation YAML and describe what it does in natural language.

YAML:
```yaml
{yaml_content}
```
{context_section}

Your task: Write a clear, concise paragraph describing:
1. What trigger starts this automation
2. What conditions must be met (if any)
3. What actions are performed
4. Any special features (delays, repeats, sequences, etc.)

Write as if explaining to a user who asked for this automation."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant expert who explains automations clearly in plain English."
                    },
                    {
                        "role": "user",
                        "content": reverse_engineering_prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=300
            )
            
            reverse_description = response.choices[0].message.content.strip()
            logger.debug(f"Reverse engineered: {reverse_description[:100]}...")
            return reverse_description
            
        except Exception as e:
            logger.error(f"Reverse engineering failed: {e}")
            return "Failed to analyze YAML"
    
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
    ) -> Dict[str, List[str]]:
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
            }
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return {
                "feedback": f"Error generating feedback: {str(e)}",
                "actions": ["Manual review recommended"]
            }
    
    async def _refine_yaml(
        self,
        original_prompt: str,
        current_yaml: str,
        feedback: Dict[str, List[str]],
        context: Optional[Dict] = None
    ) -> str:
        """
        Refine YAML based on feedback.
        
        Uses the feedback to generate improved YAML that better matches the original intent.
        """
        context_section = ""
        if context:
            context_section = f"\n\nAdditional Context:\n{self._format_context(context)}"
        
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
{context_section}

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
                return current_yaml  # Return original if refinement is invalid
            
            return refined_yaml_text
            
        except Exception as e:
            logger.error(f"YAML refinement failed: {e}")
            return current_yaml
    
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

