"""
Market Basket Analysis (Association Rules)
──────────────────────────────────────────
Method: Apriori algorithm (mlxtend) on order transaction data.

DATA STRATEGY:
  Uses REAL orders only (IsSynthetic=False via extract_basket_data()).
  Synthetic orders must NOT be included — they are generated independently
  per product and would create spurious associations that don't reflect
  real customer buying behavior.

Outputs association rules with:
  - Support    = How often items appear together in real orders
  - Confidence = P(B | A)
  - Lift       = How much more likely than by chance

Use cases:
  - Cross-sell recommendations
  - Bundle promotions
  - Product placement decisions
"""
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from .etl import extract_basket_data


def run_market_basket(min_support: float = 0.003, min_confidence: float = 0.1) -> dict:
    """
    Run Apriori on real order baskets (IsSynthetic=False only).
    Filters to multi-item baskets to compute realistic association rules.
    Returns: frequent itemsets + association rules.
    """
    df = extract_basket_data()

    if df.empty:
        return {'error': 'No data', 'rules': [], 'itemsets': []}

    # Build transaction baskets: one row per order, columns = product names
    baskets = df.groupby(['order_id', 'product_name'])['quantity'].sum().unstack(fill_value=0)
    baskets = baskets.map(lambda x: True if x > 0 else False)

    # Filter to orders containing at least 2 distinct items (co-occurrences only)
    multi_item_baskets = baskets[baskets.sum(axis=1) >= 2]

    if multi_item_baskets.empty:
        return {'error': 'Not enough multi-item transactions found.', 'rules': [], 'itemsets': []}

    # Apriori
    try:
        support_to_use = min_support
        frequent_itemsets = apriori(multi_item_baskets, min_support=support_to_use, use_colnames=True, max_len=3)
        
        if frequent_itemsets.empty:
            frequent_itemsets = apriori(multi_item_baskets, min_support=0.001, use_colnames=True, max_len=3)

        if frequent_itemsets.empty:
             return {'error': 'Not enough data patterns identified yet.', 'rules': [], 'itemsets': []}

        rules = association_rules(frequent_itemsets, metric='confidence', min_threshold=min_confidence)
        rules = rules.sort_values('lift', ascending=False)
    except Exception as e:
        return {'error': str(e), 'rules': [], 'itemsets': []}

    # Ensure variety: group by antecedent and take the top 2 rules per antecedent
    # This prevents the top 30 rules from being dominated by the 2 most popular product types
    diverse_rules = []
    seen_antecedents = {}
    for _, row in rules.iterrows():
        ant_key = tuple(row['antecedents'])
        if seen_antecedents.get(ant_key, 0) < 2:
            diverse_rules.append(row)
            seen_antecedents[ant_key] = seen_antecedents.get(ant_key, 0) + 1
            if len(diverse_rules) >= 30:
                break
                
    rules_df = pd.DataFrame(diverse_rules)

    # Format rules
    rules_data = []
    if not rules_df.empty:
        rules_data = [
            {
                'antecedents': list(row['antecedents']),
                'consequents': list(row['consequents']),
                'support': round(float(row['support']), 4),
                'confidence': round(float(row['confidence']), 4),
                'lift': round(float(row['lift']), 4),
                'interpretation': f"Customers who buy {', '.join(row['antecedents'])} "
                                  f"also tend to buy {', '.join(row['consequents'])} "
                                  f"({round(row['confidence']*100,1)}% of the time, "
                                  f"{round(row['lift'],2)}x more likely)"
            }
            for _, row in rules_df.iterrows()
        ]

    # Frequent itemsets
    itemsets_data = [
        {
            'items': list(row['itemsets']),
            'support': round(float(row['support']), 4),
            'size': len(row['itemsets'])
        }
        for _, row in frequent_itemsets.sort_values('support', ascending=False).head(20).iterrows()
    ]

    return {
        'rules': rules_data,
        'itemsets': itemsets_data,
        'model_info': {
            'method': 'Apriori (mlxtend)',
            'min_support': min_support,
            'min_confidence': min_confidence,
            'total_transactions': len(baskets),
            'rules_found': len(rules),
            'data_source': 'Real orders only (IsSynthetic=False)',
        }
    }


def get_product_recommendations(product_name: str) -> list:
    """Given a product, return its top associated products."""
    result = run_market_basket()
    rules  = result.get('rules', [])
    recommendations = []
    for rule in rules:
        if product_name in rule['antecedents']:
            recommendations.append({
                'recommended': rule['consequents'],
                'confidence': rule['confidence'],
                'lift': rule['lift'],
            })
    return sorted(recommendations, key=lambda x: x['lift'], reverse=True)[:5]
