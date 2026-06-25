"""
run_cli.py — Command-line interface for the Website Structure Planning Agent.
Model: OpenAI GPT-4o-mini  |  Scraping: Tavily API

Usage examples
──────────────
# Audit an existing website:
python run_cli.py \
  --mode audit_existing \
  --target https://yoursite.com \
  --competitors https://comp1.com https://comp2.com https://comp3.com \
  --type B2B \
  --goal "Lead Generation"

# Plan a brand-new website structure:
python run_cli.py \
  --mode new_structure \
  --target https://mynewbrand.com \
  --competitors https://comp1.com https://comp2.com \
  --type B2C \
  --goal "E-commerce"

# With pasted audit notes from a text file:
python run_cli.py \
  --mode audit_existing \
  --target https://yoursite.com \
  --competitors https://comp1.com https://comp2.com \
  --type B2B \
  --goal "Lead Generation" \
  --audit-file ./my_audit_notes.txt
"""
import argparse, sys, logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main():
    p = argparse.ArgumentParser(description="Website Structure Planning Agent (GPT-4o-mini)")
    p.add_argument("--mode",        required=True,
                   choices=["audit_existing","new_structure"],
                   help="audit_existing = fix a live site | new_structure = plan a new site")
    p.add_argument("--target",      required=True,  help="Target website URL")
    p.add_argument("--competitors", required=True,  nargs="+", help="1–5 competitor URLs")
    p.add_argument("--type",        default="B2B",  choices=["B2B","B2C"])
    p.add_argument("--goal",        default="Lead Generation",
                   choices=["Lead Generation","Demo Booking","E-commerce","Brand Awareness"])
    p.add_argument("--audit-file",  default=None,
                   help="Path to a text file with existing audit notes (optional)")
    args = p.parse_args()

    audit_text = None
    if args.audit_file:
        try:
            with open(args.audit_file, encoding="utf-8") as f:
                audit_text = f.read()
            print(f"✅  Audit notes loaded from: {args.audit_file}")
        except FileNotFoundError:
            print(f"⚠️   Audit file not found: {args.audit_file} — proceeding without it.")

    from models import AgentRequest, AnalysisMode, BusinessType, BusinessGoal
    from agents.structure_agent import run_agent

    req = AgentRequest(
        target_url      = args.target,
        mode            = AnalysisMode(args.mode),
        business_type   = BusinessType(args.type),
        business_goal   = BusinessGoal(args.goal),
        competitor_urls = args.competitors,
        audit_text      = audit_text,
    )

    print(f"\n{'='*62}")
    print(f"  Website Structure Planning Agent  —  GPT-4o-mini + Tavily")
    print(f"{'='*62}")
    print(f"  Mode          : {args.mode}")
    print(f"  Target URL    : {args.target}")
    print(f"  Business      : {args.type}  |  {args.goal}")
    print(f"  Competitors   : {len(args.competitors)} site(s)")
    if audit_text:
        print(f"  Audit notes   : {len(audit_text)} characters loaded")
    print(f"{'='*62}\n")
    print("⏳  Running agent… (typically 60–120 seconds)\n")

    result = run_agent(req)

    if result.status == "complete":
        plan = result.structure_plan
        print(f"\n{'='*62}")
        print(f"  ✅  ANALYSIS COMPLETE")
        print(f"{'='*62}")
        if plan:
            print(f"  📄  Pages planned         : {len(plan.pages)}")
            print(f"  💡  Recommendations       : {len(plan.recommendations)}")
            print(f"  🔄  Conversion paths      : {len(plan.conversion_paths)}")
        print(f"  📥  PDF saved to          : {result.pdf_path}")
        print(f"{'='*62}\n")

        if plan and plan.recommendations:
            print("Recommendations:")
            for i, r in enumerate(plan.recommendations[:5], 1):
                print(f"  {i}. {r}")

        if plan and plan.implementation_strategy:
            print("\nImplementation Strategy:")
            for step in plan.implementation_strategy[:5]:
                print(f"  ✔  {step}")

        print(f"\n📄  Full PDF report: {result.pdf_path}\n")
    else:
        print(f"\n❌  Agent failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
