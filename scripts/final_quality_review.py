"""Final quality review of all implemented recommendations."""
import subprocess
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

FILES_TO_REVIEW = [
    "services/ai-pattern-service/src/services/automation_generator.py",
    "services/ai-pattern-service/src/services/feedback_client.py",
    "services/ai-pattern-service/src/services/pattern_evolution_tracker.py",
    "services/ai-pattern-service/src/services/community_pattern_enhancer.py",
    "services/ai-pattern-service/src/pattern_analyzer/time_of_day.py",
    "services/ai-pattern-service/src/pattern_analyzer/co_occurrence.py",
    "services/ai-pattern-service/src/scheduler/pattern_analysis.py",
    "services/ai-pattern-service/src/api/synergy_router.py",
    "services/ai-pattern-service/src/api/synergy_helpers.py",
]

def main():
    print("=" * 80)
    print("FINAL QUALITY REVIEW - ALL IMPLEMENTED RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    results = []
    
    for filepath in FILES_TO_REVIEW:
        print(f"Scoring: {filepath.split('/')[-1]}...")
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "tapps_agents.cli", "reviewer", "score",
                    filepath, "--format", "json"
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60
            )
            
            if result.returncode == 0:
                import json
                try:
                    data = json.loads(result.stdout)
                    score = data.get("data", {}).get("scoring", {}).get("overall_score", 0)
                    passed = data.get("data", {}).get("passed", False)
                    results.append({
                        "file": filepath.split("/")[-1],
                        "score": score,
                        "passed": passed
                    })
                except json.JSONDecodeError:
                    results.append({
                        "file": filepath.split("/")[-1],
                        "score": 0,
                        "passed": False,
                        "error": "JSON parse error"
                    })
            else:
                results.append({
                    "file": filepath.split("/")[-1],
                    "score": 0,
                    "passed": False,
                    "error": result.stderr[:100] if result.stderr else "Unknown error"
                })
        except subprocess.TimeoutExpired:
            results.append({
                "file": filepath.split("/")[-1],
                "score": 0,
                "passed": False,
                "error": "Timeout"
            })
        except Exception as e:
            results.append({
                "file": filepath.split("/")[-1],
                "score": 0,
                "passed": False,
                "error": str(e)
            })
    
    print()
    print("-" * 80)
    print("RESULTS SUMMARY")
    print("-" * 80)
    print()
    print(f"{'File':<50} {'Score':<10} {'Status':<10}")
    print("-" * 70)
    
    total_score = 0
    passed_count = 0
    
    for r in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        score = r.get("score", 0)
        status = "[OK]" if r.get("passed") or score >= 70 else "[FAIL]"
        error = r.get("error", "")
        
        if error:
            print(f"{r['file']:<50} {'ERROR':<10} {error[:20]}")
        else:
            print(f"{r['file']:<50} {score:>6.1f}/100 {status}")
            total_score += score
            if score >= 70:
                passed_count += 1
    
    print("-" * 70)
    avg_score = total_score / len([r for r in results if not r.get("error")]) if results else 0
    print(f"{'AVERAGE':<50} {avg_score:>6.1f}/100")
    print()
    print(f"Files passing threshold (>=70): {passed_count}/{len(results)}")
    print()
    
    if passed_count == len(results):
        print("[OK] All files meet quality threshold!")
    else:
        print("[WARN] Some files need improvement")

if __name__ == "__main__":
    main()
