"""
Prompt Assembly Service
Epic AI-20 Story AI20.3: Prompt Assembly & Context Integration

Assembles prompts with context injection, token counting, and budget enforcement.
"""

import json
import logging
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..config import Settings
from ..utils.token_counter import count_message_tokens, count_tokens
from .context_builder import ContextBuilder
from .conversation_service import Conversation, ConversationService, is_generic_welcome_message
from .entity_resolution.entity_resolution_service import EntityResolutionService

logger = logging.getLogger(__name__)

# Token budget for GPT-4o (128k context, but we reserve space for response)
MAX_INPUT_TOKENS = 16_000  # Conservative limit for input tokens
RESERVED_RESPONSE_TOKENS = 4_096  # Reserve space for response


class PromptAssemblyService:
    """
    Assembles prompts with context injection, token counting, and budget enforcement.

    Epic AI-20 Story AI20.3: Prompt Assembly & Context Integration
    """

    def __init__(
        self,
        settings: Settings,
        context_builder: ContextBuilder,
        conversation_service: ConversationService,
    ):
        """
        Initialize prompt assembly service.

        Args:
            settings: Application settings
            context_builder: ContextBuilder instance for context injection
            conversation_service: ConversationService instance for message history
        """
        self.settings = settings
        self.context_builder = context_builder
        self.conversation_service = conversation_service
        self.model = settings.openai_model
        self.max_input_tokens = MAX_INPUT_TOKENS
        # Initialize EntityResolutionService and DataAPIClient for entity extraction
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self.entity_resolution_service = EntityResolutionService(
            data_api_client=self.data_api_client
        )
        logger.info("✅ Prompt assembly service initialized")

    async def assemble_messages(
        self,
        conversation_id: str,
        user_message: str,
        refresh_context: bool = False,
        skip_add_message: bool = False,
        hidden_context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """
        Assemble complete message list for OpenAI API call.

        Includes:
        - System prompt with Tier 1 context
        - Conversation history (truncated if needed)
        - New user message
        - Hidden context from proactive suggestions (if provided)

        Args:
            conversation_id: Conversation ID
            user_message: New user message to add
            refresh_context: Force context refresh (default: False, uses cache if available)
            skip_add_message: If True, skip adding the user message (use when message already added)
            hidden_context: Optional structured context from proactive agent (game_time, team_colors, etc.)

        Returns:
            List of message dicts in OpenAI format
        """
        # Get conversation
        conversation = await self.conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Add user message to conversation (unless skipping)
        if not skip_add_message:
            await self.conversation_service.add_message(
                conversation_id, "user", user_message
            )
            # Reload conversation to get updated message history (includes the message we just added)
            conversation = await self.conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found after adding message")

        # Get system prompt with context
        if refresh_context or not conversation.get_context_cache():
            logger.info(
                f"[Context Building] Conversation {conversation_id}: "
                f"Building fresh context (refresh_context={refresh_context}, "
                f"has_cache={bool(conversation.get_context_cache())})"
            )
            try:
                system_prompt = await self.context_builder.build_complete_system_prompt()
                
                # Verify system prompt was built correctly
                if not system_prompt or len(system_prompt.strip()) < 100:
                    logger.error(
                        f"[Context Building] Conversation {conversation_id}: "
                        f"⚠️ System prompt is too short or empty! Length: {len(system_prompt) if system_prompt else 0}"
                    )
                else:
                    logger.info(
                        f"[Context Building] Conversation {conversation_id}: "
                        f"✅ System prompt built successfully. Length: {len(system_prompt)} chars. "
                        f"Contains 'CRITICAL': {'CRITICAL' in system_prompt}, "
                        f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in system_prompt}"
                    )
                
                conversation.set_context_cache(system_prompt)
            except RuntimeError as e:
                if "not initialized" in str(e):
                    logger.error(
                        f"[Context Building] Conversation {conversation_id}: "
                        f"❌ CRITICAL: Context builder not initialized! Error: {e}"
                    )
                    raise
                else:
                    logger.error(
                        f"[Context Building] Conversation {conversation_id}: "
                        f"❌ Error building context: {e}"
                    )
                    raise
            except Exception as e:
                logger.error(
                    f"[Context Building] Conversation {conversation_id}: "
                    f"❌ Unexpected error building context: {e}",
                    exc_info=True
                )
                raise
        else:
            logger.debug(f"Using cached context for conversation {conversation_id}")
            system_prompt = conversation.get_context_cache()
            
            # Verify cached prompt is valid
            if not system_prompt or len(system_prompt.strip()) < 100:
                logger.warning(
                    f"[Context Building] Conversation {conversation_id}: "
                    f"⚠️ Cached system prompt is invalid (too short/empty). Rebuilding..."
                )
                system_prompt = await self.context_builder.build_complete_system_prompt()
                conversation.set_context_cache(system_prompt)

        # Inject device state context if entities mentioned in user message (Epic AI-20: Context Enhancement)
        try:
            # Extract entities from user message
            context_entities: list[dict[str, Any]] | None = None
            try:
                # Try to get entities from entity inventory service (if available)
                if hasattr(self.context_builder, '_entity_inventory_service') and \
                   self.context_builder._entity_inventory_service:
                    # Fetch entities via data_api_client (used by entity_inventory_service)
                    context_entities = await self.data_api_client.fetch_entities(limit=1000)
            except Exception as e:
                logger.debug(f"Could not fetch context entities: {e}")
                context_entities = None

            # Resolve entities from user message
            entity_result = await self.entity_resolution_service.resolve_entities(
                user_prompt=user_message,
                context_entities=context_entities,
            )

            # If entities found, fetch state context
            if entity_result.success and entity_result.matched_entities:
                entity_ids = entity_result.matched_entities
                logger.debug(
                    f"[Device State Context] Conversation {conversation_id}: "
                    f"Extracted {len(entity_ids)} entities from user message: {entity_ids[:5]}..."
                )

                # Get device state context
                state_context = await self.context_builder.get_device_state_context(
                    entity_ids=entity_ids,
                    skip_truncation=False,
                )

                # Inject state context into system prompt if available
                if state_context and state_context.strip():
                    system_prompt = f"{system_prompt}\n\n---\n\n{state_context}\n\n---\n"
                    logger.info(
                        f"[Device State Context] Conversation {conversation_id}: "
                        f"Injected device state context for {len(entity_ids)} entities"
                    )
                
                # Phase 2.3: Inject recent automation patterns if entities found
                if entity_result.success and entity_result.matched_entities:
                    try:
                        # Extract area_id from matched entities if available
                        area_id = None
                        if context_entities:
                            # Find area_id from first matched entity
                            for entity in context_entities:
                                if entity.get("entity_id") in entity_result.matched_entities:
                                    area_id = entity.get("area_id")
                                    break
                        
                        # Get recent automation patterns
                        if hasattr(self.context_builder, '_automation_patterns_service') and \
                           self.context_builder._automation_patterns_service:
                            patterns_context = await self.context_builder._automation_patterns_service.get_recent_patterns(
                                user_prompt=user_message,
                                area_id=area_id,
                                limit=3,
                                skip_truncation=False
                            )
                            
                            # Inject patterns context if available
                            if patterns_context and patterns_context.strip():
                                system_prompt = f"{system_prompt}\n\n---\n\n{patterns_context}\n\n---\n"
                                logger.info(
                                    f"[Automation Patterns] Conversation {conversation_id}: "
                                    f"Injected {len(patterns_context.split('\\n')) - 1} automation patterns"
                                )
                    except Exception as e:
                        # Graceful degradation: log error but don't fail
                        logger.debug(
                            f"[Automation Patterns] Conversation {conversation_id}: "
                            f"Failed to inject automation patterns: {e}"
                        )
        except Exception as e:
            # Graceful degradation: log error but don't fail
            logger.warning(
                f"[Device State Context] Conversation {conversation_id}: "
                f"Failed to inject device state context: {e}"
            )

        # Inject pending preview context if available (2025 Preview-and-Approval Workflow)
        pending_preview = conversation.get_pending_preview()
        if pending_preview:
            preview_context = self._build_preview_context(pending_preview)
            # Append preview context to system prompt
            system_prompt = f"{system_prompt}\n\n---\n\nPENDING AUTOMATION PREVIEW:\n{preview_context}\n\n---\n\nIMPORTANT: If the user has approved this preview, call create_automation_from_prompt with the exact same parameters (user_prompt, automation_yaml, alias) from the preview above."
            logger.info(
                f"[Preview Context] Conversation {conversation_id}: "
                f"Injected pending preview context for automation '{pending_preview.get('alias', 'unknown')}'"
            )

        # Inject hidden context from proactive suggestions (not shown to user)
        if hidden_context:
            hidden_context_str = self._build_hidden_context(hidden_context)
            system_prompt = f"{system_prompt}\n\n---\n\n{hidden_context_str}\n\n---\n"
            logger.info(
                f"[Hidden Context] Conversation {conversation_id}: "
                f"Injected proactive hidden context with {len(hidden_context)} fields"
            )

        # Get conversation history (without system prompt)
        history_messages = conversation.get_openai_messages()

        # Filter out generic welcome messages from conversation history
        # This prevents old generic responses from confusing the model
        filtered_history = []
        filtered_count = 0
        original_count = len(history_messages)
        
        for msg in history_messages:
            if msg["role"] == "assistant":
                if is_generic_welcome_message(msg.get("content", "")):
                    filtered_count += 1
                    logger.info(
                        f"[Generic Message Filter] Conversation {conversation_id}: "
                        f"Filtered generic welcome message (count: {filtered_count}). "
                        f"Content preview: {msg.get('content', '')[:100]}..."
                    )
                    continue  # Skip this generic message
            filtered_history.append(msg)
        
        history_messages = filtered_history
        
        if filtered_count > 0:
            logger.info(
                f"[Generic Message Filter] Conversation {conversation_id}: "
                f"Filtered {filtered_count} generic message(s) from history "
                f"({original_count} -> {len(history_messages)} messages)"
            )

        # Emphasize the user's current request (the last message, which should be the one we just added)
        emphasized_messages = history_messages.copy()
        
        # The user message we just added should be the last message in the history
        # Check if the last message is a user message (it should be)
        if history_messages and history_messages[-1]["role"] == "user":
            # This is the message we just added - emphasize it
            original_user_message = history_messages[-1]["content"]
            emphasized_user_message = f"""USER REQUEST (process this immediately):
{original_user_message}

Instructions: Process this request now. Use tools if needed. Do not respond with generic welcome messages."""
            
            # Replace the last message with emphasized version
            emphasized_messages[-1] = {
                "role": "user",
                "content": emphasized_user_message
            }
            
            logger.debug(
                f"[Message Emphasis] Conversation {conversation_id}: "
                f"Emphasized user request (last message). "
                f"Original length: {len(original_user_message)}, "
                f"Emphasized length: {len(emphasized_user_message)}"
            )
        else:
            # Fallback: find the last user message if the last message isn't a user message
            # (shouldn't happen, but handle gracefully)
            logger.warning(
                f"[Message Emphasis] Conversation {conversation_id}: "
                f"Last message is not a user message (role: {history_messages[-1]['role'] if history_messages else 'none'}). "
                f"Using fallback to find last user message."
            )
            
            last_user_idx = -1
            for i in range(len(history_messages) - 1, -1, -1):
                if history_messages[i]["role"] == "user":
                    last_user_idx = i
                    break
            
            if last_user_idx >= 0:
                original_user_message = history_messages[last_user_idx]["content"]
                emphasized_user_message = f"""USER REQUEST (process this immediately):
{original_user_message}

Instructions: Process this request now. Use tools if needed. Do not respond with generic welcome messages."""
                emphasized_messages[last_user_idx] = {
                    "role": "user",
                    "content": emphasized_user_message
                }
                
                logger.info(
                    f"[Message Emphasis] Conversation {conversation_id}: "
                    f"Emphasized user request using fallback (index {last_user_idx}). "
                    f"Total messages: {len(history_messages)}"
                )
            else:
                logger.error(
                    f"[Message Emphasis] Conversation {conversation_id}: "
                    f"No user message found in conversation history! "
                    f"Total messages: {len(history_messages)}"
                )

        # Verify system prompt before assembly
        if not system_prompt:
            logger.error(
                f"[Message Assembly] Conversation {conversation_id}: "
                f"❌ CRITICAL: System prompt is None or empty!"
            )
            raise ValueError("System prompt is required but was None or empty")
        
        if len(system_prompt.strip()) < 100:
            logger.error(
                f"[Message Assembly] Conversation {conversation_id}: "
                f"❌ CRITICAL: System prompt is too short ({len(system_prompt)} chars)! "
                f"Expected at least 100 chars."
            )
        
        # Assemble complete message list
        messages = [
            {"role": "system", "content": system_prompt},
            *emphasized_messages,
        ]

        # Log message assembly summary with verification
        system_msg = messages[0] if messages else None
        logger.info(
            f"[Message Assembly] Conversation {conversation_id}: "
            f"Assembled {len(messages)} messages "
            f"(1 system + {len(emphasized_messages)} history). "
            f"System prompt length: {len(system_prompt)} chars, "
            f"System message role: {system_msg['role'] if system_msg else 'MISSING'}, "
            f"System message has content: {bool(system_msg and system_msg.get('content'))}, "
            f"Contains 'CRITICAL': {'CRITICAL' in system_prompt}, "
            f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in system_prompt}, "
            f"User message: {user_message[:50]}..."
        )

        # Enforce token budget
        messages = await self._enforce_token_budget(messages, conversation)
        
        if len(messages) < len([{"role": "system", "content": system_prompt}, *emphasized_messages]):
            logger.info(
                f"[Token Budget] Conversation {conversation_id}: "
                f"Messages truncated due to token budget "
                f"({len([{'role': 'system', 'content': system_prompt}, *emphasized_messages])} -> {len(messages)})"
            )

        return messages

    async def _enforce_token_budget(
        self, messages: list[dict[str, str]], conversation: Conversation
    ) -> list[dict[str, str]]:
        """
        Enforce token budget by truncating conversation history if needed.

        Strategy:
        1. System prompt is always included (required for context)
        2. New user message is always included (required for current request)
        3. Truncate oldest conversation history messages if needed

        Args:
            messages: List of messages (system + history)
            conversation: Conversation instance (reserved for future use)

        Returns:
            Truncated message list that fits within token budget
        """
        _ = conversation  # Reserved for future use (e.g., conversation-specific token limits)
        total_tokens = count_message_tokens(messages, self.model)

        if total_tokens <= self.max_input_tokens:
            logger.debug(
                f"Token count {total_tokens} within budget {self.max_input_tokens}"
            )
            return messages

        logger.warning(
            f"Token count {total_tokens} exceeds budget {self.max_input_tokens}, "
            f"truncating conversation history"
        )

        # Extract system prompt and last user message (must keep)
        system_message = messages[0]
        last_user_message = None
        history_messages = []

        # Find last user message and separate history
        for i in range(len(messages) - 1, 0, -1):
            if messages[i]["role"] == "user":
                last_user_message = messages[i]
                history_messages = messages[1:i]  # Everything between system and last user
                break

        if not last_user_message:
            # No user message found, return system only
            logger.warning("No user message found, returning system prompt only")
            return [system_message]

        # Count tokens for required messages
        required_tokens = count_message_tokens(
            [system_message, last_user_message], self.model
        )
        available_tokens = self.max_input_tokens - required_tokens

        if available_tokens < 0:
            # Even system + user message exceeds budget (shouldn't happen)
            logger.error(
                f"System + user message ({required_tokens} tokens) exceeds budget "
                f"({self.max_input_tokens} tokens)"
            )
            return [system_message, last_user_message]

        # Truncate history to fit within available tokens
        truncated_history = self._truncate_message_list(
            history_messages, available_tokens
        )

        # Reassemble messages
        result = [system_message, *truncated_history, last_user_message]

        final_tokens = count_message_tokens(result, self.model)
        logger.info(
            f"Truncated conversation: {len(history_messages)} -> {len(truncated_history)} "
            f"messages, {total_tokens} -> {final_tokens} tokens"
        )

        return result

    def _truncate_message_list(
        self, messages: list[dict[str, str]], max_tokens: int
    ) -> list[dict[str, str]]:
        """
        Truncate message list to fit within token budget.

        P3: 2025 Optimization - Smart truncation strategy:
        - Keep recent messages (last 5-10)
        - Keep first user message (important context)
        - Remove middle messages if needed

        Args:
            messages: List of message dicts
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated message list
        """
        if not messages:
            return []

        # Count tokens for all messages
        total_tokens = count_message_tokens(messages, self.model)

        if total_tokens <= max_tokens:
            return messages

        # P3: Smart truncation - keep recent messages and first user message
        # Strategy: Keep last 10 messages + first user message, remove middle
        if len(messages) <= 10:
            # Small conversation - just remove oldest
            truncated = messages.copy()
            while truncated and count_message_tokens(truncated, self.model) > max_tokens:
                truncated.pop(0)
            return truncated

        # Find first user message
        first_user_idx = -1
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                first_user_idx = i
                break

        # Keep recent messages (last 10) and first user message if different
        recent_messages = messages[-10:]
        if first_user_idx >= 0 and first_user_idx < len(messages) - 10:
            # First user message is not in recent messages, add it
            first_user_msg = messages[first_user_idx]
            # Combine: first user + recent (avoid duplicates)
            if first_user_msg not in recent_messages:
                truncated = [first_user_msg] + recent_messages
            else:
                truncated = recent_messages
        else:
            truncated = recent_messages

        # If still too large, remove oldest from truncated list
        while truncated and count_message_tokens(truncated, self.model) > max_tokens:
            # Remove oldest, but keep first user message if present
            if len(truncated) > 1 and truncated[0].get("role") == "user" and len(truncated) > 2:
                # Keep first user, remove second oldest
                truncated.pop(1)
            else:
                truncated.pop(0)

        return truncated

    async def get_token_count(
        self, conversation_id: str, include_new_message: str | None = None
    ) -> dict[str, int]:
        """
        Get token count breakdown for a conversation.

        Args:
            conversation_id: Conversation ID
            include_new_message: Optional new message to include in count

        Returns:
            Dictionary with token counts:
            - system_tokens: System prompt tokens
            - history_tokens: Conversation history tokens
            - new_message_tokens: New message tokens (if provided)
            - total_tokens: Total tokens
        """
        conversation = await self.conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Get system prompt
        system_prompt = conversation.get_context_cache()
        if not system_prompt:
            system_prompt = await self.context_builder.build_complete_system_prompt()
            conversation.set_context_cache(system_prompt)

        system_tokens = count_tokens(system_prompt, self.model)

        # Get history messages
        history_messages = conversation.get_openai_messages()
        history_tokens = count_message_tokens(history_messages, self.model)

        # Count new message if provided
        new_message_tokens = 0
        if include_new_message:
            new_message = {"role": "user", "content": include_new_message}
            new_message_tokens = count_message_tokens([new_message], self.model)

        total_tokens = system_tokens + history_tokens + new_message_tokens

        return {
            "system_tokens": system_tokens,
            "history_tokens": history_tokens,
            "new_message_tokens": new_message_tokens,
            "total_tokens": total_tokens,
            "max_input_tokens": self.max_input_tokens,
            "within_budget": total_tokens <= self.max_input_tokens,
        }

    def _build_preview_context(self, preview: dict) -> str:
        """
        Build context string from pending preview for system prompt injection.

        Args:
            preview: Preview dictionary from preview_automation_from_prompt tool

        Returns:
            Formatted context string
        """
        lines = [
            f"Automation Name: {preview.get('alias', 'Unknown')}",
            f"User Prompt: {preview.get('user_prompt', 'Unknown')}",
            "",
            "Automation YAML:",
            "```yaml",
            preview.get('automation_yaml', ''),
            "```",
        ]
        
        details = preview.get('details', {})
        if details:
            lines.extend([
                "",
                "Details:",
                f"- Trigger: {details.get('trigger_description', 'Unknown')}",
                f"- Action: {details.get('action_description', 'Unknown')}",
                f"- Mode: {details.get('mode', 'single')}",
            ])
        
        entities = preview.get('entities_affected', [])
        if entities:
            lines.append(f"- Entities Affected: {', '.join(entities)}")
        
        areas = preview.get('areas_affected', [])
        if areas:
            lines.append(f"- Areas Affected: {', '.join(areas)}")
        
        services = preview.get('services_used', [])
        if services:
            lines.append(f"- Services Used: {', '.join(services)}")
        
        warnings = preview.get('safety_warnings', [])
        if warnings:
            lines.extend([
                "",
                "Safety Warnings:",
            ])
            for warning in warnings:
                lines.append(f"- {warning}")
        
        validation = preview.get('validation', {})
        if validation:
            errors = validation.get('errors', [])
            warnings_list = validation.get('warnings', [])
            if errors:
                lines.extend([
                    "",
                    "Validation Errors:",
                ])
                for error in errors:
                    lines.append(f"- {error}")
            if warnings_list:
                lines.extend([
                    "",
                    "Validation Warnings:",
                ])
                for warning in warnings_list:
                    lines.append(f"- {warning}")
        
        return "\n".join(lines)

    def _build_hidden_context(self, hidden_context: dict[str, Any]) -> str:
        """
        Build context string from proactive agent hidden context.
        
        This context is injected into the system prompt but NOT shown to users.
        It helps the LLM make better automation decisions with structured data
        that the proactive agent gathered (game times, team colors, etc.).

        Args:
            hidden_context: Dictionary with automation hints from proactive agent

        Returns:
            Formatted context string for system prompt injection
        """
        lines = [
            "## PROACTIVE CONTEXT (from suggestion engine - not visible to user)",
            "",
            "The following context was gathered by the proactive suggestion engine.",
            "Use this information to create accurate automations:",
            "",
        ]
        
        # Game time (for sports automations)
        if game_time := hidden_context.get("game_time"):
            lines.append(f"- **Game Time**: {game_time}")
        
        # Kickoff countdown
        if kickoff_in := hidden_context.get("kickoff_in"):
            lines.append(f"- **Kickoff In**: {kickoff_in}")
        
        # Team colors (for lighting automations)
        if team_colors := hidden_context.get("team_colors"):
            if isinstance(team_colors, list) and len(team_colors) >= 1:
                lines.append(f"- **Team Colors**: Primary: {team_colors[0]}")
                if len(team_colors) >= 2:
                    lines.append(f"                  Secondary: {team_colors[1]}")
        
        # Trigger type recommendation
        if trigger_type := hidden_context.get("trigger_type"):
            lines.append(f"- **Recommended Trigger Type**: {trigger_type}")
        
        # Trigger entity (e.g., Team Tracker sensor)
        if trigger_entity := hidden_context.get("trigger_entity"):
            lines.append(f"- **Trigger Entity**: {trigger_entity}")
        
        # Trigger condition
        if trigger_condition := hidden_context.get("trigger_condition"):
            lines.append(f"- **Trigger Condition**: {trigger_condition}")
        
        # Target color (RGB)
        if target_color := hidden_context.get("target_color"):
            lines.append(f"- **Target Color**: {target_color}")
        
        # Context type (sports, weather, energy, etc.)
        if context_type := hidden_context.get("context_type"):
            lines.append(f"- **Context Type**: {context_type}")
        
        # Blueprint constraint mode (Epic Blueprint Suggestions)
        if hidden_context.get("constraint_mode") == "blueprint":
            lines.append("")
            lines.append("---")
            lines.append("BLUEPRINT CONSTRAINT MODE:")
            lines.append("---")
            lines.append("You are working with a Home Assistant Blueprint.")
            
            blueprint_id = hidden_context.get("blueprint_id")
            blueprint_yaml = hidden_context.get("blueprint_yaml")
            blueprint_inputs = hidden_context.get("blueprint_inputs", {})
            matched_devices = hidden_context.get("matched_devices", [])
            
            if blueprint_id:
                lines.append(f"Blueprint ID: {blueprint_id}")
            if blueprint_yaml:
                lines.append("Blueprint YAML structure:")
                lines.append("```yaml")
                # Include first 500 chars of YAML to show structure
                yaml_preview = blueprint_yaml[:500] + ("..." if len(blueprint_yaml) > 500 else "")
                lines.append(yaml_preview)
                lines.append("```")
            if blueprint_inputs:
                lines.append("Blueprint Input Schema:")
                lines.append(json.dumps(blueprint_inputs, indent=2))
            if matched_devices:
                device_list = ", ".join([
                    str(d.get("friendly_name") or d.get("entity_id", ""))
                    for d in matched_devices
                ])
                lines.append(f"Matched Devices: {device_list}")
            
            lines.append("")
            lines.append("CRITICAL CONSTRAINTS:")
            lines.append("- You MUST stay within the blueprint's input schema")
            lines.append("- Only modify input values, NOT the blueprint structure")
            lines.append("- Suggest valid entity IDs that match the blueprint's domain/device_class requirements")
            lines.append("- Do NOT create new automations outside the blueprint scope")
            lines.append("- The blueprint is proven and tested - work within its constraints")
            lines.append("---")
            lines.append("")
        
        # Any additional fields
        standard_fields = {
            "game_time", "kickoff_in", "team_colors", "trigger_type", 
            "trigger_entity", "trigger_condition", "target_color", "context_type",
            "constraint_mode", "blueprint_id", "blueprint_yaml", "blueprint_inputs", "matched_devices"
        }
        for key, value in hidden_context.items():
            if key not in standard_fields and value:
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        
        lines.extend([
            "",
            "⚠️ IMPORTANT: Use sensor state triggers for sports events, NOT fixed times.",
            "If game_time is provided, it's for informational display only - trigger on sensor state change.",
        ])
        
        return "\n".join(lines)
