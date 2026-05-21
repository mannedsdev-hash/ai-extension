#!/usr/bin/env python3
"""margin-scorer: Amazon FBA unit economics calculator.

Pure calculation, no network calls. Reads the fee schedule and thresholds
from config/ so every number stays editable. Prints a JSON result to stdout.

Usage:
    python calc.py --sell-price 24.99 --landed-cost 6.50 --category kitchen
    python calc.py --sell-price 24.99 --landed-cost 6.50 \
        --category pet_supplies --fba-tier large_standard_8to12oz \
        --target-acos 0.30 --overhead-rate 0.05
"""
import argparse
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_referral_rate(fees, category):
    table = fees["referral_fee_rate"]
    if category:
        key = category.strip().lower().replace(" ", "_").replace("&", "and")
        if key in table["by_category"]:
            return table["by_category"][key], key
    return table["default"], "default"


def pick_fba_fee(fees, tier_id):
    by_id = {t["id"]: t for t in fees["fba_fulfillment_fee"]["tiers"]}
    if tier_id and tier_id in by_id:
        return by_id[tier_id]["fee"], tier_id
    default = fees["fba_fulfillment_fee"]["default_tier"]
    return by_id[default]["fee"], default


def compute(args, fees, thresholds):
    referral_rate, referral_key = pick_referral_rate(fees, args.category)
    fba_fee, fba_tier = pick_fba_fee(fees, args.fba_tier)
    min_referral = fees.get("minimum_referral_fee", 0.0)

    price = args.sell_price
    landed = args.landed_cost
    acos = args.target_acos
    overhead_rate = args.overhead_rate

    referral_fee = max(referral_rate * price, min_referral)
    ad_cost = acos * price
    overhead = overhead_rate * price
    total_cost = landed + referral_fee + fba_fee + ad_cost + overhead
    profit = price - total_cost
    net_margin = profit / price if price else 0.0

    # Closed-form solves below use the referral percentage rate and ignore
    # the small fixed referral minimum, which only binds at very low prices.
    variable_rate = referral_rate + acos + overhead_rate
    fixed = landed + fba_fee

    denom_breakeven = 1.0 - variable_rate
    breakeven_price = fixed / denom_breakeven if denom_breakeven > 0 else None

    target_margin = thresholds["margin"]["minimum_net_margin"]
    denom_reco = 1.0 - target_margin - variable_rate
    recommended_price = fixed / denom_reco if denom_reco > 0 else None

    return {
        "inputs": {
            "sell_price": price,
            "landed_cost": landed,
            "category": args.category or None,
            "referral_category_used": referral_key,
            "referral_fee_rate": referral_rate,
            "fba_tier_used": fba_tier,
            "target_acos": acos,
            "overhead_rate": overhead_rate,
        },
        "costs": {
            "landed_cost": round(landed, 2),
            "referral_fee": round(referral_fee, 2),
            "fba_fulfillment_fee": round(fba_fee, 2),
            "est_ad_cost": round(ad_cost, 2),
            "overhead": round(overhead, 2),
            "total_cost_per_unit": round(total_cost, 2),
        },
        "result": {
            "profit_per_unit": round(profit, 2),
            "net_margin_pct": round(net_margin * 100, 1),
            "breakeven_price": round(breakeven_price, 2) if breakeven_price else None,
            "recommended_sell_price": round(recommended_price, 2) if recommended_price else None,
            "minimum_net_margin_pct": round(target_margin * 100, 1),
            "below_threshold": net_margin < target_margin,
        },
    }


def main():
    p = argparse.ArgumentParser(description="Amazon FBA unit economics calculator")
    p.add_argument("--sell-price", type=float, required=True)
    p.add_argument("--landed-cost", type=float, required=True,
                   help="COGS + inbound shipping + duties, per unit")
    p.add_argument("--category", type=str, default="",
                   help="Category key for referral-fee lookup (see config/amazon-fees.json)")
    p.add_argument("--fba-tier", type=str, default="",
                   help="FBA size-tier id (see config/amazon-fees.json)")
    p.add_argument("--target-acos", type=float, default=None,
                   help="Target ad cost of sale as a fraction. Default: thresholds.json")
    p.add_argument("--overhead-rate", type=float, default=None,
                   help="Overhead (storage, returns) as a fraction of price. Default: thresholds.json")
    p.add_argument("--config-dir", type=str, default=os.path.join(REPO_ROOT, "config"))
    args = p.parse_args()

    fees = load_json(os.path.join(args.config_dir, "amazon-fees.json"))
    thresholds = load_json(os.path.join(args.config_dir, "thresholds.json"))

    if args.target_acos is None:
        args.target_acos = thresholds["margin"]["default_target_acos"]
    if args.overhead_rate is None:
        args.overhead_rate = thresholds["margin"]["overhead_rate"]

    json.dump(compute(args, fees, thresholds), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
