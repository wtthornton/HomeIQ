"""Review quality report for implemented recommendations."""
import json
import sys

def main():
    try:
        with open('reports/quality/quality-report.json', 'r') as f:
            data = json.load(f)
        
        print("=" * 80)
        print("QUALITY REPORT SUMMARY")
        print("=" * 80)
        
        summary = data.get('summary', {})
        print(f"Overall Score: {summary.get('overall_score', 'N/A'):.1f}/100")
        print(f"Files Analyzed: {summary.get('files_analyzed', 'N/A')}")
        print(f"Quality Gate: {'PASSED' if summary.get('passed') else 'FAILED'}")
        
        print("\n" + "-" * 80)
        print("FILE SCORES")
        print("-" * 80)
        
        files = data.get('files', [])
        for f in sorted(files, key=lambda x: x.get('score', 0), reverse=True):
            path = f.get('path', 'unknown')
            filename = path.split('/')[-1] if '/' in path else path.split('\\')[-1]
            score = f.get('score', 0)
            status = 'PASS' if score >= 70 else 'FAIL'
            metrics = f.get('metrics', {})
            complexity = metrics.get('complexity', 'N/A')
            security = metrics.get('security', 'N/A')
            maintainability = metrics.get('maintainability', 'N/A')
            print(f"  {filename:45} {score:5.1f}/100  [{status}]")
            print(f"    Complexity: {complexity}/10, Security: {security}/10, Maintainability: {maintainability}/10")
        
        print("\n" + "=" * 80)
        print("FILES NEEDING IMPROVEMENT (Score < 70)")
        print("=" * 80)
        
        needs_improvement = [f for f in files if f.get('score', 0) < 70]
        if needs_improvement:
            for f in needs_improvement:
                path = f.get('path', 'unknown')
                filename = path.split('/')[-1] if '/' in path else path.split('\\')[-1]
                score = f.get('score', 0)
                print(f"  {filename}: {score:.1f}/100")
        else:
            print("  All files meet quality threshold!")
        
    except FileNotFoundError:
        print("Error: Quality report not found. Run reviewer report first.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing quality report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
