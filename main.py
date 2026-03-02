import json, argparse, sys, os
from src.igc_parser import IGCParser
from src.scorer import RASATScorer
from src.visualizer import Visualizer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="IGC file path")
    parser.add_argument("--config", default="task_config.json")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)

    with open(args.config, 'r') as f:
        config = json.load(f)
    
    points = IGCParser(args.input).parse()
    scorer = RASATScorer(points, config)
    res = scorer.calculate_results()

    # แสดง Error ใน Console แต่ไม่หยุดรัน เพื่อให้เห็นพล็อต
    if not res["is_valid"]:
        print(f"!!! WARNING: {res['status_message']} !!!")
    
    print(f"--- {config['task_name']} ---")
    print(f"Triangle: {res['triangle_km']} km | Effective: {res['effective_km']} km")
    
    # สั่ง Plot เสมอไม่ว่าจะ Error หรือไม่
    Visualizer.plot_task_result(points, res['vertices'], res, config)

if __name__ == "__main__":
    main()