"""
Reporting functionality for Ask AI continuous improvement.

Handles:
- Saving cycle and prompt data
- Generating summaries
- Analyzing results
- Creating improvement plans
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Any
from dataclasses import asdict

from .config import OUTPUT_DIR, SCORE_EXCELLENT_THRESHOLD, SCORE_WARNING_THRESHOLD, YAML_VALIDITY_THRESHOLD
from .models import CycleResult, PromptResult
from .prompts import TARGET_PROMPTS
from .terminal_output import TerminalOutput


class Reporter:
    """Handles all reporting functionality for improvement cycles"""
    
    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cycles: list[CycleResult] = []
    
    def save_cycle_data(
        self, 
        cycle_num: int, 
        result: CycleResult, 
        workflow_data: dict[str, Any]
    ) -> None:
        """Save all cycle data to files"""
        cycle_dir = self.output_dir / f"cycle-{cycle_num}"
        cycle_dir.mkdir(exist_ok=True)
        
        # Save overall cycle summary
        cycle_summary = {
            'cycle_number': cycle_num,
            'overall_score': result.overall_score,
            'all_successful': result.all_successful,
            'timestamp': result.timestamp,
            'prompt_results': [
                {
                    'prompt_id': pr.prompt_id,
                    'prompt_name': pr.prompt_name,
                    'complexity': pr.complexity,
                    'total_score': pr.total_score,
                    'success': pr.success,
                    'error': pr.error
                }
                for pr in result.prompt_results
            ]
        }
        with open(cycle_dir / "cycle_summary.json", 'w', encoding='utf-8') as f:
            json.dump(cycle_summary, f, indent=2)
        
        # Save cycle result object
        with open(cycle_dir / "cycle_result.json", 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        # Save logs
        log_file = cycle_dir / "logs.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Cycle {cycle_num} Execution Log\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {result.timestamp}\n")
            f.write(f"Overall Score: {result.overall_score:.2f}/100\n")
            f.write(f"All Successful: {result.all_successful}\n")
            f.write(f"Number of Prompts: {len(result.prompt_results)}\n\n")
            for pr in result.prompt_results:
                f.write(f"  {pr.prompt_name} ({pr.complexity}): ")
                if pr.success:
                    f.write(f"✓ {pr.total_score:.2f}/100\n")
                else:
                    f.write(f"✗ Failed: {pr.error}\n")
        
        TerminalOutput.print_info(f"Cycle {cycle_num} data saved to {cycle_dir}")
    
    def save_prompt_data(
        self,
        cycle_num: int,
        prompt_id: str,
        prompt_result: PromptResult,
        workflow_data: dict[str, Any]
    ) -> None:
        """Save individual prompt data to files"""
        prompt_dir = self.output_dir / f"cycle-{cycle_num}" / prompt_id
        prompt_dir.mkdir(parents=True, exist_ok=True)
        
        if workflow_data.get('query_response'):
            with open(prompt_dir / "query_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['query_response'], f, indent=2)
        
        if prompt_result.clarification_log:
            with open(prompt_dir / "clarification_rounds.json", 'w', encoding='utf-8') as f:
                json.dump(prompt_result.clarification_log, f, indent=2)
        
        if workflow_data.get('clarification_response'):
            with open(prompt_dir / "clarification_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['clarification_response'], f, indent=2)
        
        if workflow_data.get('selected_suggestion'):
            with open(prompt_dir / "suggestion_selected.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['selected_suggestion'], f, indent=2)
        
        if workflow_data.get('approval_response'):
            with open(prompt_dir / "approval_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['approval_response'], f, indent=2)
        
        if prompt_result.automation_yaml:
            with open(prompt_dir / "automation.yaml", 'w', encoding='utf-8') as f:
                f.write(prompt_result.automation_yaml)
        
        # Save prompt scores
        scores = {
            'automation_score': prompt_result.automation_score,
            'yaml_score': prompt_result.yaml_score,
            'clarification_rounds': prompt_result.clarification_rounds,
            'total_score': prompt_result.total_score,
            'success': prompt_result.success,
            'error': prompt_result.error
        }
        with open(prompt_dir / "score.json", 'w', encoding='utf-8') as f:
            json.dump(scores, f, indent=2)
        
        with open(prompt_dir / "result.json", 'w', encoding='utf-8') as f:
            json.dump(asdict(prompt_result), f, indent=2, default=str)
    
    def generate_summary(self) -> str:
        """Generate summary of all cycles"""
        summary_lines = [
            "# Ask AI Continuous Improvement Summary",
            "",
            f"Generated: {datetime.now().isoformat()}",
            f"Total Cycles: {len(self.cycles)}",
            f"Prompts per Cycle: {len(TARGET_PROMPTS)}",
            "",
            "## Cycle Results",
            ""
        ]
        
        for i, cycle in enumerate(self.cycles, 1):
            status_icon = "[SUCCESS]" if cycle.all_successful else "[PARTIAL]" if any(r.success for r in cycle.prompt_results) else "[FAILED]"
            summary_lines.extend([
                f"### Cycle {i}",
                f"- **Status**: {status_icon}",
                f"- **Overall Score**: {cycle.overall_score:.2f}/100",
                f"- **All Successful**: {cycle.all_successful}",
                f"- **Timestamp**: {cycle.timestamp}",
                "",
                "#### Prompt Results:",
                ""
            ])
            
            for pr in cycle.prompt_results:
                prompt_status = "✓" if pr.success else "✗"
                summary_lines.append(f"- {prompt_status} **{pr.prompt_name}** ({pr.complexity}): {pr.total_score:.2f}/100")
                if pr.error:
                    summary_lines.append(f"  - Error: {pr.error}")
            
            summary_lines.append("")
        
        # Trends
        if len(self.cycles) > 1:
            summary_lines.extend([
                "## Improvement Trends",
                ""
            ])
            
            overall_scores = [c.overall_score for c in self.cycles if c.overall_score > 0]
            if overall_scores:
                summary_lines.extend([
                    f"- **Overall Score Range**: {min(overall_scores):.2f} - {max(overall_scores):.2f}",
                    f"- **Average Overall Score**: {sum(overall_scores)/len(overall_scores):.2f}",
                    f"- **Final Overall Score**: {overall_scores[-1]:.2f}",
                    ""
                ])
            
            # Per-prompt trends
            for prompt_info in TARGET_PROMPTS:
                prompt_id = prompt_info['id']
                prompt_scores = []
                for cycle in self.cycles:
                    pr = next((r for r in cycle.prompt_results if r.prompt_id == prompt_id), None)
                    if pr and pr.success:
                        prompt_scores.append(pr.total_score)
                
                if prompt_scores:
                    summary_lines.extend([
                        f"- **{prompt_info['name']}** ({prompt_info['complexity']}): "
                        f"Range {min(prompt_scores):.2f}-{max(prompt_scores):.2f}, "
                        f"Avg {sum(prompt_scores)/len(prompt_scores):.2f}, "
                        f"Final {prompt_scores[-1]:.2f}",
                        ""
                    ])
        
        return "\n".join(summary_lines)
    
    def analyze_cycle(
        self, 
        cycle_num: int, 
        result: PromptResult, 
        workflow_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze cycle results and identify improvement areas.
        Returns analysis dict with recommendations.
        """
        analysis = {
            'cycle': cycle_num,
            'issues': [],
            'recommendations': [],
            'improvement_areas': []
        }
        
        # Analyze clarification count
        if result.clarification_rounds > 3:
            analysis['issues'].append(f"High clarification count: {result.clarification_rounds}")
            analysis['recommendations'].append(
                "Improve entity extraction to reduce clarification questions"
            )
            analysis['improvement_areas'].append('entity_extraction')
        
        # Analyze automation correctness
        if result.automation_score < 80:
            analysis['issues'].append(f"Low automation correctness: {result.automation_score:.2f}")
            analysis['recommendations'].append(
                "Review prompt engineering and YAML generation logic"
            )
            analysis['improvement_areas'].append('prompt_engineering')
        
        # Analyze YAML validity
        if result.yaml_score < 100:
            analysis['issues'].append(f"YAML validity issues: {result.yaml_score:.2f}")
            analysis['recommendations'].append(
                "Fix YAML generation to ensure valid Home Assistant format"
            )
            analysis['improvement_areas'].append('yaml_generation')
        
        # Analyze total score
        if result.total_score < SCORE_WARNING_THRESHOLD:
            analysis['issues'].append(f"Total score below threshold: {result.total_score:.2f}")
            analysis['recommendations'].append(
                "Multiple areas need improvement - review all components"
            )
        
        return analysis
    
    def create_improvement_plan(self, cycle_num: int, analysis: dict[str, Any]) -> str:
        """
        Create improvement plan based on analysis.
        Returns markdown formatted plan.
        """
        plan_lines = [
            f"# Improvement Plan - Cycle {cycle_num}",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Issues Identified",
            ""
        ]
        
        if analysis['issues']:
            for issue in analysis['issues']:
                plan_lines.append(f"- {issue}")
        else:
            plan_lines.append("- No critical issues identified")
        
        plan_lines.extend([
            "",
            "## Recommendations",
            ""
        ])
        
        if analysis['recommendations']:
            for rec in analysis['recommendations']:
                plan_lines.append(f"- {rec}")
        else:
            plan_lines.append("- Continue current approach")
        
        plan_lines.extend([
            "",
            "## Improvement Areas",
            ""
        ])
        
        improvement_areas = {
            'entity_extraction': {
                'files': [
                    'services/ai-automation-service/src/api/ask_ai_router.py',
                    'services/ai-automation-service/src/services/clarification/detector.py'
                ],
                'actions': [
                    'Improve entity extraction logic',
                    'Add better device name matching',
                    'Reduce ambiguity detection false positives'
                ]
            },
            'prompt_engineering': {
                'files': [
                    'services/ai-automation-service/src/api/ask_ai_router.py',
                    'services/ai-automation-service/src/services/clarification/question_generator.py'
                ],
                'actions': [
                    'Enhance prompt templates',
                    'Add more context to OpenAI requests',
                    'Improve instruction clarity'
                ]
            },
            'yaml_generation': {
                'files': [
                    'services/ai-automation-service/src/api/ask_ai_router.py:2170'
                ],
                'actions': [
                    'Fix YAML structure validation',
                    'Ensure all required fields are present',
                    'Validate entity ID formats'
                ]
            }
        }
        
        for area in analysis['improvement_areas']:
            if area in improvement_areas:
                info = improvement_areas[area]
                plan_lines.extend([
                    f"### {area.replace('_', ' ').title()}",
                    "",
                    "**Files to modify:**",
                    ""
                ])
                for file in info['files']:
                    plan_lines.append(f"- `{file}`")
                plan_lines.extend([
                    "",
                    "**Proposed actions:**",
                    ""
                ])
                for action in info['actions']:
                    plan_lines.append(f"- {action}")
                plan_lines.append("")
        
        return "\n".join(plan_lines)
    
    def save_summary(self, summary: str) -> Path:
        """Save summary to file"""
        summary_path = self.output_dir / "SUMMARY.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        return summary_path
    
    def save_improvement_plan(self, cycle_num: int, plan: str) -> Path:
        """Save improvement plan to file"""
        cycle_dir = self.output_dir / f"cycle-{cycle_num}"
        plan_path = cycle_dir / "IMPROVEMENT_PLAN.md"
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.write(plan)
        return plan_path

